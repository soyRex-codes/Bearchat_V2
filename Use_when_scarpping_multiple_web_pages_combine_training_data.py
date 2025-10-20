"""
Combine Multiple Training JSON Files
=====================================
Merges multiple training data files into one large dataset.
Use this when you've collected data from multiple MSU pages.

Usage:
    python combine_training_data.py
"""

import json
import os
from datetime import datetime

def combine_json_files():
    """Combine all training JSON files in current directory."""
    
    # Find all JSON files with training data
    json_files = []
    for file in os.listdir('.'):
        if file.endswith('_training.json') and file.startswith(('smart_', 'msu_')):
            json_files.append(file)
    
    if not json_files:
        print(" No training JSON files found!")
        print("   Looking for files like: smart_*_training.json or msu_*_training.json")
        return
    
    print(f"\n Found {len(json_files)} training files:")
    for f in json_files:
        print(f"   - {f}")
    
    # Load and combine all data
    all_data = []
    stats = {}
    
    for file in json_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Track stats
            if isinstance(data, list):
                all_data.extend(data)
                
                # Count by content_type
                for item in data:
                    if 'metadata' in item:
                        content_type = item['metadata'].get('content_type', 'unknown')
                        topic = item['metadata'].get('topic', 'unknown')
                        
                        if content_type not in stats:
                            stats[content_type] = {'count': 0, 'topics': set()}
                        
                        stats[content_type]['count'] += 1
                        stats[content_type]['topics'].add(topic)

                print(f"   {file}: {len(data)} examples")
            else:
                print(f"    {file}: Not a list format, skipping")
                
        except Exception as e:
            print(f"   {file}: Error - {e}")

    if not all_data:
        print("\n No data to combine!")
        return
    
    # Save combined data
    output_file = f"combined_msu_training_{datetime.now().strftime('%Y%m%d')}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print(f" COMBINED SUCCESSFULLY")
    print(f"{'='*80}")
    print(f"\n Total Examples: {len(all_data)}")
    print(f" Output File: {output_file}")
    
    # Show breakdown by content type
    print("\n Breakdown by Category:")
    for content_type, info in sorted(stats.items()):
        print(f"\n   {content_type.replace('_', ' ').title()}: {info['count']} examples")
        print(f"   Topics:")
        for topic in sorted(info['topics'])[:3]:  # Show first 3 topics
            print(f"      • {topic}")
        if len(info['topics']) > 3:
            print(f"      • ... and {len(info['topics']) - 3} more")
    
    # Recommendations
    print(f"\n{'='*80}")
    print(f" Next Steps:")
    print(f"{'='*80}")
    print(f"1. Review the combined file:")
    print(f"   cat {output_file} | head -n 50")
    print(f"\n2. Update your training script:")
    print(f'   data = load_dataset("json", data_files="{output_file}", split="train")')
    print(f"\n3. Train the model:")
    print(f"   python enhanced_finetune.py")
    
    # Quality check
    print(f"\n💡 Quality Tips:")
    if len(all_data) < 100:
        print(f"     You have {len(all_data)} examples - aim for 500+ for best results")
    elif len(all_data) < 300:
        print(f"     You have {len(all_data)} examples - good start! Aim for 500+ for better performance")
    else:
        print(f"     You have {len(all_data)} examples - great dataset size!")

    if len(stats) < 3:
        print(f"     Only {len(stats)} categories - collect more diverse topics!")
    else:
        print(f"     {len(stats)} categories - good diversity!")


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("COMBINE TRAINING DATA FILES")
    print("="*80)
    
    try:
        combine_json_files()
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
