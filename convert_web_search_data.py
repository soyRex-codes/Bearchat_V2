#!/usr/bin/env python3
"""
Web Search Training Data Converter
===================================
Converts web_search_data_collection.txt to training format for fine-tuning

Usage:
    python convert_web_search_data.py

Output:
    web_search_training_data.json - Ready for fine-tuning
"""

import json
from datetime import datetime
from pathlib import Path

def convert_to_training_format(input_file='web_search_data_collection.txt', 
                                output_file='web_search_training_data.json'):
    """
    Convert collected web search data to training format
    
    Input format (JSON Lines):
    {
        "timestamp": "2025-11-14T10:30:00",
        "question": "What are current CS courses?",
        "answer": "Based on the MSU website...",
        "citations": [...],
        "topic": "Computer Science",
        "content_type": "academic"
    }
    
    Output format (Training):
    [
        {
            "instruction": "What are current CS courses?",
            "input": "",
            "output": "Based on the MSU website...",
            "topic": "Computer Science",
            "content_type": "academic",
            "metadata": {
                "source": "web_search",
                "date_collected": "2025-11-14",
                "citations": [...]
            }
        }
    ]
    """
    
    if not Path(input_file).exists():
        print(f"❌ Input file not found: {input_file}")
        print("   No web search data collected yet.")
        return
    
    training_data = []
    line_count = 0
    error_count = 0
    
    print(f"📖 Reading from: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
                
                # Convert to training format
                training_entry = {
                    "instruction": entry.get("question", ""),
                    "input": "",  # Empty for direct Q&A format
                    "output": entry.get("answer", ""),
                    "topic": entry.get("topic", "Unknown"),
                    "content_type": entry.get("content_type", "general"),
                    "metadata": {
                        "source": "web_search",
                        "date_collected": entry.get("timestamp", "").split("T")[0],
                        "citations": entry.get("citations", []),
                        "model_version": entry.get("model_version", "unknown")
                    }
                }
                
                training_data.append(training_entry)
                line_count += 1
                
            except json.JSONDecodeError as e:
                error_count += 1
                print(f"⚠️  Line {line_num}: Invalid JSON - {e}")
            except Exception as e:
                error_count += 1
                print(f"⚠️  Line {line_num}: Error - {e}")
    
    if not training_data:
        print("❌ No valid training data found")
        return
    
    # Save training data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    # Statistics
    print(f"\n✅ Conversion complete!")
    print(f"   📊 Total entries: {line_count}")
    print(f"   ⚠️  Errors: {error_count}")
    print(f"   💾 Output: {output_file}")
    print(f"   📦 Size: {Path(output_file).stat().st_size / 1024:.1f} KB")
    
    # Show topic breakdown
    topic_counts = {}
    content_type_counts = {}
    
    for entry in training_data:
        topic = entry.get('topic', 'Unknown')
        content_type = entry.get('content_type', 'general')
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
        content_type_counts[content_type] = content_type_counts.get(content_type, 0) + 1
    
    print(f"\n📊 Topic Breakdown:")
    for topic, count in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {topic}: {count}")
    
    print(f"\n📊 Content Type Breakdown:")
    for ctype, count in sorted(content_type_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"   • {ctype}: {count}")
    
    # Sample entry
    if training_data:
        print(f"\n📝 Sample Entry:")
        sample = training_data[0]
        print(f"   Instruction: {sample['instruction'][:60]}...")
        print(f"   Output: {sample['output'][:60]}...")
        print(f"   Topic: {sample['topic']}")
        print(f"   Citations: {len(sample['metadata']['citations'])}")

def view_recent_entries(input_file='web_search_data_collection.txt', count=5):
    """View the most recent collected entries"""
    
    if not Path(input_file).exists():
        print(f"❌ No data file found: {input_file}")
        return
    
    entries = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
    
    if not entries:
        print("📭 No entries found")
        return
    
    print(f"\n📋 Last {min(count, len(entries))} Web Search Queries:\n")
    
    for i, entry in enumerate(entries[-count:], 1):
        print(f"{'='*60}")
        print(f"Entry #{len(entries) - count + i}")
        print(f"{'='*60}")
        print(f"🕐 Time: {entry.get('timestamp', 'N/A')}")
        print(f"❓ Question: {entry.get('question', 'N/A')}")
        print(f"📚 Topic: {entry.get('topic', 'N/A')}")
        print(f"🏷️  Type: {entry.get('content_type', 'N/A')}")
        print(f"🔗 Citations: {len(entry.get('citations', []))}")
        
        if entry.get('citations'):
            print(f"\n   Sources:")
            for j, cite in enumerate(entry['citations'][:3], 1):
                print(f"   [{j}] {cite.get('title', 'Untitled')[:50]}")
                print(f"       {cite.get('url', '')[:60]}")
        
        print(f"\n💬 Answer Preview:")
        answer = entry.get('answer', '')
        preview = answer[:200] + '...' if len(answer) > 200 else answer
        print(f"   {preview}")
        print()

def get_statistics(input_file='web_search_data_collection.txt'):
    """Get statistics about collected data"""
    
    if not Path(input_file).exists():
        print(f"❌ No data file found: {input_file}")
        return
    
    entries = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
    
    if not entries:
        print("📭 No data collected yet")
        return
    
    total = len(entries)
    
    # Date range
    dates = [e.get('timestamp', '') for e in entries if e.get('timestamp')]
    first_date = min(dates).split('T')[0] if dates else 'N/A'
    last_date = max(dates).split('T')[0] if dates else 'N/A'
    
    # Topic counts
    topics = {}
    for e in entries:
        topic = e.get('topic', 'Unknown')
        topics[topic] = topics.get(topic, 0) + 1
    
    # Citation counts
    total_citations = sum(len(e.get('citations', [])) for e in entries)
    avg_citations = total_citations / total if total > 0 else 0
    
    print(f"\n📊 Web Search Data Statistics")
    print(f"{'='*60}")
    print(f"Total Entries: {total}")
    print(f"Date Range: {first_date} to {last_date}")
    print(f"Total Citations: {total_citations}")
    print(f"Avg Citations per Query: {avg_citations:.1f}")
    print(f"\nTop Topics:")
    for topic, count in sorted(topics.items(), key=lambda x: x[1], reverse=True)[:10]:
        percentage = (count / total) * 100
        print(f"  • {topic}: {count} ({percentage:.1f}%)")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    import sys
    
    print("🔄 Web Search Training Data Converter\n")
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "view":
            count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            view_recent_entries(count=count)
        
        elif command == "stats":
            get_statistics()
        
        elif command == "convert":
            input_file = sys.argv[2] if len(sys.argv) > 2 else 'web_search_data_collection.txt'
            output_file = sys.argv[3] if len(sys.argv) > 3 else 'web_search_training_data.json'
            convert_to_training_format(input_file, output_file)
        
        else:
            print("Unknown command. Use: convert, view, or stats")
    
    else:
        # Default: show stats and convert
        get_statistics()
        print()
        convert_to_training_format()
        print(f"\n✨ Ready for fine-tuning with: web_search_training_data.json")
