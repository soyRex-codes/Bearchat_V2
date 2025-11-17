import 'dart:developer';

import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/services.dart'; // For clipboard
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'api_service.dart';
import 'package:file_picker/file_picker.dart';
import 'package:url_launcher/url_launcher.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  try {
    await dotenv.load(fileName: ".env");
  } catch (e) {
    // If .env file fails to load, continue with default values
    log('Warning: .env file not found, using default API URL');
  }

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'BearChat',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.blue,
          brightness: Brightness.light,
        ),
        useMaterial3: true,
        scaffoldBackgroundColor: Colors.white,
        appBarTheme: const AppBarTheme(centerTitle: true, elevation: 0),
      ),
      home: const ChatScreen(),
    );
  }
}

class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final String? fileName;
  final String? processingMethod;
  final int? characterCount;
  final int? numChunks;
  final String? messageId; // Unique ID for regeneration
  final List<Map<String, String>>? citations; // Web search citations

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.fileName,
    this.processingMethod,
    this.characterCount,
    this.numChunks,
    String? messageId,
    this.citations,
  }) : messageId = messageId ?? '${timestamp.millisecondsSinceEpoch}';
}

// Helper function to extract and open URLs
Future<void> _launchURL(String url) async {
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    url = 'https://$url';
  }

  try {
    if (await canLaunchUrl(Uri.parse(url))) {
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    }
  } catch (e) {
    debugPrint('Could not launch $url: $e');
  }
}

// Helper function to detect URLs in text
List<TextSpan> _buildTextSpans(
  String text,
  TextStyle baseStyle,
  bool isUserMessage,
) {
  final List<TextSpan> spans = [];
  final RegExp urlRegex = RegExp(
    r'(?:(?:https?|ftp):\/\/)?(?:www\.)?[a-z0-9]+(?:[.\-][a-z0-9]+)*\.[a-z]{2,}(?:\/[^\s]*)?',
    caseSensitive: false,
  );

  int lastIndex = 0;

  for (final match in urlRegex.allMatches(text)) {
    // Add text before the URL
    if (match.start > lastIndex) {
      spans.add(
        TextSpan(
          text: text.substring(lastIndex, match.start),
          style: baseStyle,
        ),
      );
    }

    // Add the URL as clickable link
    final url = match.group(0)!;
    spans.add(
      TextSpan(
        text: url,
        style: baseStyle.copyWith(
          color: const Color(0xFF2196F3),
          decoration: TextDecoration.underline,
        ),
        recognizer: TapGestureRecognizer()..onTap = () => _launchURL(url),
      ),
    );

    lastIndex = match.end;
  }

  // Add any remaining text
  if (lastIndex < text.length) {
    spans.add(TextSpan(text: text.substring(lastIndex), style: baseStyle));
  }

  return spans.isEmpty ? [TextSpan(text: text, style: baseStyle)] : spans;
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<ChatMessage> _messages = [];
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _isLoading = false;
  PlatformFile? _selectedFile;
  bool _isUploadingFile = false;
  int _retryCount = 0; // Track retry attempts
  bool _webSearchEnabled = false; // User-controlled web search toggle

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _copyToClipboard(String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Copied to clipboard!'),
        duration: Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  Future<void> _regenerateResponse(int messageIndex) async {
    if (messageIndex < 1) return; // Need a previous user message

    // Find the user question that triggered this response
    final userMessage = _messages[messageIndex - 1];
    if (!userMessage.isUser) return;

    // Remove the old AI response
    setState(() {
      _messages.removeAt(messageIndex);
      _isLoading = true;
    });

    try {
      // Get conversation history up to this point
      final historyUpToNow = _messages.sublist(0, messageIndex - 1);

      // Regenerate response
      final response = await ApiService.sendMessage(
        userMessage.text,
        historyUpToNow,
        webSearchEnabled: _webSearchEnabled,
      );

      final aiResponse = response['answer'] as String;
      final citations = response['citations'] as List<Map<String, String>>?;

      setState(() {
        _isLoading = false;
        // Insert at the same position
        _messages.insert(
          messageIndex,
          ChatMessage(
            text: aiResponse,
            isUser: false,
            timestamp: DateTime.now(),
            citations: citations,
          ),
        );
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _messages.insert(
          messageIndex,
          ChatMessage(
            text: 'Error regenerating response: ${e.toString()}',
            isUser: false,
            timestamp: DateTime.now(),
          ),
        );
      });
    }

    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());
  }

  Future<void> _pickAndUploadDocument() async {
    try {
      FilePickerResult? result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['pdf', 'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'gif'],
      );

      if (result != null && result.files.isNotEmpty) {
        setState(() {
          _selectedFile = result.files.first;
        });
      }
    } catch (e) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text('Error picking file: $e')));
    }
  }

  void _clearSelectedFile() {
    setState(() {
      _selectedFile = null;
    });
  }

  void _scrollToBottom() {
    if (_scrollController.hasClients) {
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeOut,
      );
    }
  }

  void _clearChat() {
    setState(() {
      _messages.clear();
    });
  }

  Future<void> _showClearChatDialog() async {
    if (_messages.isEmpty) return;

    final shouldClear = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Clear Chat'),
          content: const Text('Are you sure you want to clear all messages?'),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.of(context).pop(true),
              child: const Text('Clear', style: TextStyle(color: Colors.red)),
            ),
          ],
        );
      },
    );

    if (shouldClear == true) {
      _clearChat();
    }
  }

  Future<void> _handleSubmitted(String text) async {
    if (text.trim().isEmpty && _selectedFile == null) return;

    _textController.clear();

    // Add user message
    setState(() {
      _messages.add(
        ChatMessage(
          text: text.isEmpty ? '📎 ${_selectedFile?.name}' : text,
          isUser: true,
          timestamp: DateTime.now(),
          fileName: _selectedFile?.name,
        ),
      );
      _isLoading = true;
      _isUploadingFile = _selectedFile != null;
    });

    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());

    try {
      if (_selectedFile != null) {
        // Upload document mode
        // On web, path is unavailable and throws an exception when accessed
        // So we use try-catch and fall back to empty string
        String pathToUse = '';
        try {
          pathToUse = _selectedFile!.path ?? '';
        } catch (e) {
          // Path is unavailable on web, use empty string
          pathToUse = '';
        }

        final response = await ApiService.uploadDocument(
          filePath: pathToUse,
          file: _selectedFile!,
          question: text.isEmpty ? 'Analyze this document' : text,
        );

        // Add AI message with document info
        setState(() {
          _isLoading = false;
          _isUploadingFile = false;
          _messages.add(
            ChatMessage(
              text: response.answer,
              isUser: false,
              timestamp: DateTime.now(),
              fileName: response.documentInfo.fileName,
              processingMethod: response.documentInfo.processingMethod,
              characterCount: response.documentInfo.numCharacters,
              numChunks: response.documentInfo.numChunks,
            ),
          );
        });
        _clearSelectedFile();
      } else {
        // Regular chat mode
        final response = await ApiService.sendMessage(
          text,
          _messages,
          webSearchEnabled: _webSearchEnabled,
        );
        final aiResponse = response['answer'] as String;
        final citations = response['citations'] as List<Map<String, String>>?;

        setState(() {
          _isLoading = false;
          _isUploadingFile = false;
          _messages.add(
            ChatMessage(
              text: aiResponse,
              isUser: false,
              timestamp: DateTime.now(),
              citations: citations,
            ),
          );
        });
      }
    } catch (e) {
      // Handle error with better messaging
      String errorMessage = 'Sorry, I encountered an error.';

      if (e.toString().contains('timeout')) {
        errorMessage =
            'Request timeout. The server took too long to respond. Please try again.';
      } else if (e.toString().contains('Network error') ||
          e.toString().contains('SocketException')) {
        errorMessage =
            'Network error. Please check your connection and make sure the server is running.';
      } else if (e.toString().contains('Server error (500)')) {
        errorMessage =
            'Server error. The model may be loading or experiencing issues. Please try again in a moment.';
      } else if (e.toString().contains('Server unavailable (503)')) {
        errorMessage =
            'Server unavailable. Please make sure the API server is running.';
      } else {
        errorMessage = 'Error: ${e.toString()}';
      }

      setState(() {
        _isLoading = false;
        _isUploadingFile = false;
        _messages.add(
          ChatMessage(
            text: errorMessage,
            isUser: false,
            timestamp: DateTime.now(),
          ),
        );
      });
    }

    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToBottom());
  }

  Widget _buildMessage(ChatMessage message) {
    final baseTextStyle = TextStyle(
      color: message.isUser ? Colors.white : Colors.black87,
      fontSize: 15,
      height: 1.5,
      fontFamily: 'Roboto',
    );

    final messageIndex = _messages.indexOf(message);

    return Align(
      alignment: message.isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 8, horizontal: 12),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          color: message.isUser ? const Color(0xFF2196F3) : Colors.grey[100],
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(18),
            topRight: const Radius.circular(18),
            bottomLeft: message.isUser
                ? const Radius.circular(18)
                : const Radius.circular(4),
            bottomRight: message.isUser
                ? const Radius.circular(4)
                : const Radius.circular(18),
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.08),
              blurRadius: 2,
              offset: const Offset(0, 1),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            // Main message text with clickable links
            RichText(
              text: TextSpan(
                children: _buildTextSpans(
                  message.text,
                  baseTextStyle,
                  message.isUser,
                ),
              ),
            ),
            // Action buttons for AI messages (copy, regenerate)
            if (!message.isUser && !message.text.startsWith('Error:')) ...[
              const SizedBox(height: 8),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Copy button
                  InkWell(
                    onTap: () => _copyToClipboard(message.text),
                    borderRadius: BorderRadius.circular(4),
                    child: Padding(
                      padding: const EdgeInsets.all(4),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(Icons.copy, size: 14, color: Colors.grey[600]),
                          const SizedBox(width: 4),
                          Text(
                            'Copy',
                            style: TextStyle(
                              fontSize: 11,
                              color: Colors.grey[600],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  // Regenerate button
                  InkWell(
                    onTap: () => _regenerateResponse(messageIndex),
                    borderRadius: BorderRadius.circular(4),
                    child: Padding(
                      padding: const EdgeInsets.all(4),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.refresh,
                            size: 14,
                            color: Colors.grey[600],
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'Regenerate',
                            style: TextStyle(
                              fontSize: 11,
                              color: Colors.grey[600],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ],
            // Show document info if available (for AI responses with documents)
            if (!message.isUser && message.fileName != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.grey[200],
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.grey[300]!, width: 0.5),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SelectableText(
                      '📄 ${message.fileName}',
                      style: const TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: Colors.black87,
                      ),
                    ),
                    if (message.processingMethod != null) ...[
                      const SizedBox(height: 6),
                      SelectableText(
                        'Method: ${message.processingMethod}',
                        style: TextStyle(fontSize: 11, color: Colors.grey[700]),
                      ),
                    ],
                    if (message.characterCount != null) ...[
                      const SizedBox(height: 6),
                      SelectableText(
                        'Characters: ${message.characterCount}',
                        style: TextStyle(fontSize: 11, color: Colors.grey[700]),
                      ),
                    ],
                    if (message.numChunks != null) ...[
                      const SizedBox(height: 6),
                      SelectableText(
                        'Sections: ${message.numChunks}',
                        style: TextStyle(fontSize: 11, color: Colors.grey[700]),
                      ),
                    ],
                  ],
                ),
              ),
            ],
            // Show web search citations if available
            if (!message.isUser &&
                message.citations != null &&
                message.citations!.isNotEmpty) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.blue[50],
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue[200]!, width: 0.5),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        Icon(Icons.search, size: 14, color: Colors.blue[700]),
                        const SizedBox(width: 6),
                        Text(
                          'Sources (${message.citations!.length})',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                            color: Colors.blue[900],
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ...message.citations!.asMap().entries.map((entry) {
                      final index = entry.key;
                      final cite = entry.value;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: InkWell(
                          onTap: () => _launchURL(cite['url'] ?? ''),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '[${index + 1}] ',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: Colors.blue[700],
                                ),
                              ),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      cite['title'] ?? 'Untitled',
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w500,
                                        color: Colors.blue[800],
                                        decoration: TextDecoration.underline,
                                      ),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      cite['url'] ?? '',
                                      style: TextStyle(
                                        fontSize: 10,
                                        color: Colors.grey[600],
                                      ),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    }).toList(),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'BearChat',
          style: TextStyle(fontWeight: FontWeight.w600, fontSize: 22),
        ),
        centerTitle: true,
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        elevation: 1,
        shadowColor: Colors.black.withValues(alpha: 0.1),
        actions: [
          // Web search toggle button
          Tooltip(
            message: _webSearchEnabled
                ? 'Web search ON (using Google)'
                : 'Web search OFF (model only)',
            child: IconButton(
              icon: Icon(
                _webSearchEnabled
                    ? Icons.travel_explore
                    : Icons.travel_explore_outlined,
                color: _webSearchEnabled ? Colors.green : Colors.grey[600],
              ),
              onPressed: () {
                setState(() {
                  _webSearchEnabled = !_webSearchEnabled;
                });
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(
                      _webSearchEnabled
                          ? '🔍 Web search enabled - Will search MSU websites for current info'
                          : '📚 Web search disabled - Using model knowledge only',
                    ),
                    duration: const Duration(seconds: 2),
                    behavior: SnackBarBehavior.floating,
                  ),
                );
              },
            ),
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline),
            onPressed: _showClearChatDialog,
            tooltip: 'Clear chat',
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: GestureDetector(
                onTap: () {
                  // Hide keyboard when tapping outside the input field
                  FocusScope.of(context).unfocus();
                },
                child: _messages.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.chat_bubble_outline,
                              size: 80,
                              color: Colors.grey[350],
                            ),
                            const SizedBox(height: 24),
                            Text(
                              'Start chatting with Boomer!',
                              style: TextStyle(
                                fontSize: 20,
                                fontWeight: FontWeight.w500,
                                color: Colors.grey[600],
                              ),
                            ),
                            const SizedBox(height: 12),
                            Padding(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 32,
                              ),
                              child: Text(
                                'Ask questions about Missouri State University',
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 14,
                                  color: Colors.grey[500],
                                ),
                              ),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        controller: _scrollController,
                        padding: const EdgeInsets.symmetric(
                          vertical: 16,
                          horizontal: 8,
                        ),
                        itemCount: _messages.length,
                        keyboardDismissBehavior:
                            ScrollViewKeyboardDismissBehavior.onDrag,
                        itemBuilder: (context, index) {
                          return Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: _buildMessage(_messages[index]),
                          );
                        },
                      ),
              ),
            ),
            if (_isLoading)
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 14,
                ),
                child: Row(
                  children: [
                    SizedBox(
                      width: 20,
                      height: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.grey[600],
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text(
                      _isUploadingFile
                          ? 'Processing document and generating response...'
                          : 'Boomer is thinking...',
                      style: TextStyle(
                        color: Colors.grey[600],
                        fontStyle: FontStyle.italic,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
            Container(
              decoration: BoxDecoration(
                color: Theme.of(context).scaffoldBackgroundColor,
                border: Border(
                  top: BorderSide(color: Colors.grey[200]!, width: 1),
                ),
              ),
              child: Padding(
                padding: EdgeInsets.only(
                  left: 14,
                  right: 14,
                  top: 12,
                  bottom: MediaQuery.of(context).viewInsets.bottom > 0
                      ? 10
                      : 14,
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Show selected file preview
                    if (_selectedFile != null)
                      Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(
                            0xFF2196F3,
                          ).withValues(alpha: 0.08),
                          border: Border.all(
                            color: const Color(
                              0xFF2196F3,
                            ).withValues(alpha: 0.3),
                            width: 1,
                          ),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              _selectedFile!.name.endsWith('.pdf')
                                  ? Icons.picture_as_pdf
                                  : Icons.image,
                              color: const Color(0xFF2196F3),
                              size: 22,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(
                                    _selectedFile!.name,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontWeight: FontWeight.w500,
                                      fontSize: 14,
                                    ),
                                  ),
                                  Text(
                                    '${(_selectedFile!.size / 1024).toStringAsFixed(1)} KB',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: Colors.grey[600],
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.close, size: 20),
                              onPressed: _clearSelectedFile,
                              padding: EdgeInsets.zero,
                              constraints: const BoxConstraints(),
                            ),
                          ],
                        ),
                      ),
                    // Message input row
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        // File upload button (like ChatGPT/Claude)
                        IconButton(
                          icon: const Icon(Icons.attach_file),
                          onPressed: _pickAndUploadDocument,
                          tooltip: 'Attach file (PDF/Image)',
                          color: const Color(0xFF2196F3),
                          padding: const EdgeInsets.all(10),
                          constraints: const BoxConstraints(),
                        ),
                        const SizedBox(width: 6),
                        // Message input field
                        Expanded(
                          child: Container(
                            decoration: BoxDecoration(
                              color: Colors.grey[50],
                              borderRadius: BorderRadius.circular(24),
                              border: Border.all(
                                color: Colors.grey[200]!,
                                width: 1,
                              ),
                            ),
                            child: TextField(
                              controller: _textController,
                              decoration: InputDecoration(
                                hintText: _selectedFile != null
                                    ? 'Ask about this file...'
                                    : 'Message Boomer...',
                                hintStyle: TextStyle(
                                  color: Colors.grey[500],
                                  fontSize: 15,
                                ),
                                border: InputBorder.none,
                                contentPadding: const EdgeInsets.symmetric(
                                  horizontal: 18,
                                  vertical: 12,
                                ),
                              ),
                              maxLines: 5,
                              minLines: 1,
                              textInputAction: TextInputAction.send,
                              onSubmitted: _handleSubmitted,
                              textCapitalization: TextCapitalization.sentences,
                              style: const TextStyle(fontSize: 15),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        // Send button
                        Container(
                          decoration: const BoxDecoration(
                            color: Color(0xFF2196F3),
                            shape: BoxShape.circle,
                          ),
                          child: IconButton(
                            icon: const Icon(
                              Icons.arrow_upward,
                              color: Colors.white,
                              size: 20,
                            ),
                            onPressed: () =>
                                _handleSubmitted(_textController.text),
                            tooltip: 'Send',
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
