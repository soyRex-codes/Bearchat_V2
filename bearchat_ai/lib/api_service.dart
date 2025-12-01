import 'dart:convert';
import 'package:file_picker/file_picker.dart' as fp;
import 'package:http/http.dart' as http;
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:path/path.dart' as path;
import 'main.dart'; // Import ChatMessage from main.dart

class ApiService {
  static String get baseUrl =>
      dotenv.env['API_BASE_URL'] ??
      'http://10.13.11.125:8080'; // Default URL # use env variable if available

  // Retry configuration
  static const int maxRetries = 3;
  static const Duration initialRetryDelay = Duration(seconds: 2);

  /// Exponential backoff retry logic for network requests
  static Future<T> _retryRequest<T>(
    Future<T> Function() request, {
    int maxAttempts = maxRetries,
    Duration initialDelay = initialRetryDelay,
  }) async {
    int attempt = 0;
    Duration delay = initialDelay;

    while (true) {
      try {
        return await request();
      } catch (e) {
        attempt++;
        if (attempt >= maxAttempts) {
          // Max retries reached, throw the error
          rethrow;
        }

        // Wait with exponential backoff
        print(
          'Retry attempt $attempt/$maxAttempts after ${delay.inSeconds}s...',
        );
        await Future.delayed(delay);
        delay = delay * 2; // Exponential backoff
      }
    }
  }

  /// Send a chat message to the fine-tuned model with conversation memory and retry logic
  static Future<Map<String, dynamic>> sendMessage(
    String question,
    List<ChatMessage> conversationHistory, {
    bool webSearchEnabled = false,
  }) async {
    return await _retryRequest(() async {
      try {
        // Build conversation history from last 3-5 messages (exclude current question)
        List<Map<String, String>> historyForAPI = [];

        // Get last 6 messages (3 Q&A pairs), skip the user's current message
        int startIndex = conversationHistory.length > 6
            ? conversationHistory.length - 6
            : 0;
        for (int i = startIndex; i < conversationHistory.length; i++) {
          final msg = conversationHistory[i];

          if (msg.isUser) {
            // This is a question
            historyForAPI.add({'question': msg.text, 'answer': ''});
          } else {
            // This is an answer - attach to previous question
            if (historyForAPI.isNotEmpty) {
              historyForAPI.last['answer'] = msg.text;
            }
          }
        }

        // Remove incomplete pairs (questions without answers)
        historyForAPI.removeWhere((pair) => pair['answer']!.isEmpty);

        // Send request WITH conversation history and web search preference
        final response = await http
            .post(
              Uri.parse('$baseUrl/chat'),
              headers: {'Content-Type': 'application/json'},
              body: json.encode({
                'question': question,
                'conversation_history': historyForAPI, // Include history
                'web_search_enabled': webSearchEnabled, // User preference
              }),
            )
            .timeout(
              const Duration(
                seconds: 120,
              ), // Increased to 2 minutes for M4 Mac processing
              onTimeout: () {
                throw Exception(
                  'Request timeout - server took too long to respond',
                );
              },
            );

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          String answer = data['answer'] ?? 'No response from model';

          // Clean up the response by removing excessive # symbols
          answer = _cleanResponse(answer);

          // Extract citations if available
          List<Map<String, String>> citations = [];
          if (data['metrics'] != null && data['metrics']['citations'] != null) {
            final citationsData = data['metrics']['citations'] as List;
            citations = citationsData
                .map(
                  (cite) => {
                    'title': cite['title']?.toString() ?? '',
                    'url': cite['url']?.toString() ?? '',
                    'snippet': cite['snippet']?.toString() ?? '',
                  },
                )
                .toList();
          }

          // Log cache performance (optional)
          if (data['metrics'] != null) {
            final metrics = data['metrics'];
            print(
              'Response metrics: cached=${metrics['cached']}, '
              'time=${metrics['total_time']?.toStringAsFixed(2)}s, '
              'web_search=${metrics['web_search_used']}, '
              'citations=${citations.length}',
            );
          }

          return {'answer': answer, 'citations': citations};
        } else if (response.statusCode == 500) {
          // Server error - might be recoverable with retry
          throw Exception('Server error (500) - retrying...');
        } else if (response.statusCode == 503) {
          // Service unavailable - server might be starting
          throw Exception('Server unavailable (503) - retrying...');
        } else {
          // Other errors - don't retry
          throw Exception(
            'Server error: ${response.statusCode} (non-retryable)',
          );
        }
      } on http.ClientException catch (e) {
        // Network error - retryable
        throw Exception('Network error: $e - retrying...');
      } catch (e) {
        // Re-throw to trigger retry or final error
        rethrow;
      }
    });
  }

  /// Clean up the response text
  static String _cleanResponse(String text) {
    // Remove excessive # symbols (more than 2 consecutive)
    text = text.replaceAll(RegExp(r'#{3,}'), '');

    // Remove standalone # symbols that are not part of markdown headers
    text = text.replaceAll(RegExp(r'\s#\s'), ' ');

    // Remove # at the beginning or end of lines if they're excessive
    text = text.replaceAll(RegExp(r'^#+\s*$', multiLine: true), '');

    // Clean up multiple newlines
    text = text.replaceAll(RegExp(r'\n{3,}'), '\n\n');

    // Trim whitespace
    text = text.trim();

    return text;
  }

  /// Check server health with retry logic
  static Future<bool> checkHealth() async {
    try {
      return await _retryRequest(
        () async {
          final response = await http
              .get(Uri.parse('$baseUrl/health'))
              .timeout(const Duration(seconds: 5));

          return response.statusCode == 200;
        },
        maxAttempts: 2, // Only retry once for health checks
      );
    } catch (e) {
      return false;
    }
  }

  /// Send multiple questions in batch
  static Future<List<String>> sendBatchMessages(List<String> questions) async {
    try {
      final response = await http
          .post(
            Uri.parse('$baseUrl/batch'),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({'questions': questions}),
          )
          .timeout(const Duration(seconds: 60));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        return List<String>.from(data['answers'] ?? []);
      } else {
        throw Exception('Server error: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to get batch response: $e');
    }
  }

  /// Upload document (PDF or image) and ask a question about it
  /// Works on both native (iOS/Android/macOS) and web platforms
  static Future<DocumentUploadResponse> uploadDocument({
    required String filePath,
    required String question,
    required fp.PlatformFile file,
    int maxLength =
        600, // Increased for detailed document analysis (transcripts, etc.)
    double temperature = 0.3,
    double topP = 0.85,
  }) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/upload'));

      // Add file - use bytes if available (web), otherwise use path (native)
      try {
        // Try bytes first (works on web and sometimes on native)
        if (file.bytes != null && file.bytes!.isNotEmpty) {
          request.files.add(
            http.MultipartFile.fromBytes(
              'file',
              file.bytes!,
              filename: file.name,
            ),
          );
        } else if (filePath.isNotEmpty) {
          // Fall back to path (native platforms)
          request.files.add(
            await http.MultipartFile.fromPath(
              'file',
              filePath,
              filename: path.basename(filePath),
            ),
          );
        } else {
          throw Exception('No valid file provided');
        }
      } catch (e) {
        // If path access fails on web, ensure we have bytes
        if (file.bytes != null && file.bytes!.isNotEmpty) {
          request.files.add(
            http.MultipartFile.fromBytes(
              'file',
              file.bytes!,
              filename: file.name,
            ),
          );
        } else {
          rethrow;
        }
      }

      // Add form fields
      request.fields['question'] = question;
      request.fields['max_length'] = maxLength.toString();
      request.fields['temperature'] = temperature.toString();
      request.fields['top_p'] = topP.toString();

      // Send request with timeout
      final streamedResponse = await request.send().timeout(
        const Duration(
          seconds: 480,
        ), // 8 minutes for document processing (increased from 5)
        onTimeout: () {
          throw Exception(
            'Request timeout - document processing took too long (>8 min)',
          );
        },
      );

      // Get response
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final data = json.decode(response.body);

        if (data['success'] == true) {
          return DocumentUploadResponse(
            success: true,
            answer: _cleanResponse(data['answer'] ?? 'No response'),
            question: data['question'] ?? question,
            documentInfo: DocumentInfo.fromJson(data['document_info'] ?? {}),
            topic: data['topic'],
            contentType: data['content_type'],
          );
        } else {
          throw Exception(data['error'] ?? 'Upload failed');
        }
      } else {
        final errorData = json.decode(response.body);
        throw Exception(
          errorData['error'] ?? 'Server error: ${response.statusCode}',
        );
      }
    } catch (e) {
      throw Exception('Failed to upload document: $e');
    }
  }
}

/// Response model for document upload
class DocumentUploadResponse {
  final bool success;
  final String answer;
  final String question;
  final DocumentInfo documentInfo;
  final String? topic;
  final String? contentType;

  DocumentUploadResponse({
    required this.success,
    required this.answer,
    required this.question,
    required this.documentInfo,
    this.topic,
    this.contentType,
  });
}

/// Document information model
class DocumentInfo {
  final String fileName;
  final String fileType;
  final String processingMethod;
  final int numCharacters;
  final int? numChunks;

  DocumentInfo({
    required this.fileName,
    required this.fileType,
    required this.processingMethod,
    required this.numCharacters,
    this.numChunks,
  });

  factory DocumentInfo.fromJson(Map<String, dynamic> json) {
    return DocumentInfo(
      fileName: json['file_name'] ?? 'Unknown',
      fileType: json['file_type'] ?? 'unknown',
      processingMethod: json['processing_method'] ?? 'unknown',
      numCharacters: json['num_characters'] ?? 0,
      numChunks: json['num_chunks'],
    );
  }
}
