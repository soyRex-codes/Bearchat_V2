#!/usr/bin/env python3
"""
Rollback to Previous Checkpoint
================================
Use this if your latest training produced a bad model.
Restores the previous (backup) checkpoint.

Usage:
    python rollback_checkpoint.py
"""

import os
import shutil

CHECKPOINT_DIR = "./models"
LATEST_DIR = os.path.join(CHECKPOINT_DIR, "latest")
PREVIOUS_DIR = os.path.join(CHECKPOINT_DIR, "previous")

def rollback():
    """Rollback to previous checkpoint."""
    print("\n" + "="*80)
    print("⏮  CHECKPOINT ROLLBACK")
    print("="*80)
    
    # Check if previous exists
    if not os.path.exists(PREVIOUS_DIR):
        print("\n No previous checkpoint found!")
        print("   Cannot rollback - no backup available.")
        return False
    
    # Check if latest exists
    if not os.path.exists(LATEST_DIR):
        print("\n  Latest checkpoint doesn't exist")
        print("   Nothing to rollback from.")
        return False
    
    print(f"\n Current Status:")
    print(f"   Latest: {LATEST_DIR}/")
    print(f"   Previous: {PREVIOUS_DIR}/")
    
    print(f"\n  This will:")
    print(f"   1. Delete current 'latest' checkpoint")
    print(f"   2. Restore 'previous' checkpoint as 'latest'")
    
    response = input(f"\n❓ Proceed with rollback? (y/n): ").strip().lower()
    
    if response != 'y':
        print("\n Rollback cancelled")
        return False
    
    print(f"\n  Removing current latest checkpoint...")
    shutil.rmtree(LATEST_DIR)
    print(f"    Removed")
    
    print(f"\n Restoring previous checkpoint...")
    shutil.copytree(PREVIOUS_DIR, LATEST_DIR)
    print(f"    Restored")
    
    print("\n" + "="*80)
    print(" ROLLBACK COMPLETE!")
    print("="*80)
    print(f"\n Your model has been restored to the previous version.")
    print(f"   Test it: python chat_contextual.py")
    
    return True

def main():
    try:
        rollback()
    except Exception as e:
        print(f"\n Error during rollback: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
