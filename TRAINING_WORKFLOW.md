# 🎯 New Safe Training Workflow

## 📁 Model Directory Structure

```
models/
├── production/          # Your SAFE manual backup (NEVER auto-deleted)
├── staging/            # Auto-saved after each training (test before promoting)
└── checkpoint-YYYYMMDD-HHMMSS/  # Temporary training runs (auto-cleanup)
```

## 🔄 Complete Workflow

### 1️⃣ Train a Model

```bash
python finetune.py
```

**What happens:**
- ✅ Trains on your JSON data
- ✅ Saves to temporary checkpoint (timestamped)
- ✅ Asks if you want to save to staging
- ✅ **If interrupted:** No changes to any model (SAFE!)
- ✅ Cleans up old checkpoints (keeps last 3)

**After training:**
```
❓ Save this trained model to staging? (yes/no): yes
```

### 2️⃣ Test the Staging Model

```bash
# Test staging (default)
python test_model.py

# Or test production
python test_model.py --production
```

**What to check:**
- ✅ Answer quality
- ✅ Hallucination/mixing
- ✅ Response coherence
- ✅ Context handling

### 3️⃣ Promote to Production (Manual)

**Only when satisfied with staging model:**

```bash
python promote_model.py
```

**What happens:**
- ✅ Backs up current production → `production-backup-YYYYMMDD-HHMMSS/`
- ✅ Copies staging → production
- ✅ Keeps staging unchanged (safe rollback)
- ✅ **Your control:** You decide when to promote

**Example:**
```
❓ Promote staging to production? (yes/no): yes
```

### 4️⃣ Use in API/App

```bash
python api_server.py
```

**Model selection priority:**
1. **Production** (if exists) - Your safe, tested model
2. **Staging** (fallback) - Latest trained model
3. **Latest** (old setup) - Legacy support

## 🛡️ Safety Features

### ✅ No More Accidental Deletions

| Scenario | Old System | New System |
|----------|-----------|------------|
| **Training interrupted** | ❌ Model deleted | ✅ No changes |
| **Bad training** | ❌ Overwrites good model | ✅ Staging only |
| **Testing needed** | ❌ No test environment | ✅ Staging model |
| **Rollback** | ❌ Lost previous | ✅ Production safe |

### 🔒 Production Model

- **Never auto-deleted**
- **Never auto-overwritten**
- **Manual promotion only**
- **You control when to update**

## 📝 Example Session

```bash
# 1. Train
python finetune.py
# → Saves to checkpoint-20251102-143022/
# → "Save to staging? yes"
# → Staging updated

# 2. Test
python test_model.py
# → Tests staging model
# → Check if answers are good

# 3. If good → Promote
python promote_model.py
# → "Promote to production? yes"
# → Production updated

# 4. If bad → Train again
python finetune.py
# → Old staging overwritten
# → Production still safe

# 5. Use in production
python api_server.py
# → Loads production model
# → Serves to Flutter app
```

## 🎓 Best Practices

### When to Promote to Production

✅ **Good times:**
- Tested thoroughly in staging
- Answer quality improved
- No hallucinations
- Meets your requirements

❌ **Bad times:**
- Haven't tested yet
- Uncertain about quality
- Still experimenting
- Training just finished

### Backup Strategy

1. **Production** = Your "gold" model (manual updates)
2. **Staging** = Test new models here
3. **Checkpoints** = Auto-cleanup (keep last 3)

### Rollback Options

If new production model has issues:

```bash
# Option 1: Restore from backup
cp -r models/production-backup-YYYYMMDD-HHMMSS models/production

# Option 2: Use old staging
# (if you didn't train again)

# Option 3: Use backup checkpoint
# (from checkpoint-YYYYMMDD-HHMMSS/)
```

## 🚀 Migration from Old System

If you have `models/latest/` and `models/previous/`:

```bash
# Promote current model to production (first time)
cp -r models/latest models/production

# Or if latest is broken, use previous
cp -r models/previous models/production

# Then train normally
python finetune.py
```

## 💡 Tips

1. **Always test in staging first**
2. **Keep production stable** (don't promote untested models)
3. **Train often** (staging is disposable)
4. **Promote rarely** (only when satisfied)
5. **Trust your production model** (it's your manual backup)

## 🔧 Commands Reference

```bash
# Train (safe - nothing deleted on interrupt)
python finetune.py

# Test staging (default)
python test_model.py

# Test production
python test_model.py --production

# Promote staging → production (manual)
python promote_model.py

# Run API (uses production by default)
python api_server.py
```

## ❓ FAQ

**Q: What if I interrupt training?**  
A: Nothing happens! Temporary checkpoint is discarded, staging/production unchanged.

**Q: Can I train multiple times before promoting?**  
A: Yes! Each training overwrites staging, but production stays safe.

**Q: What if promoted model is bad?**  
A: Restore from `production-backup-YYYYMMDD-HHMMSS/` directory.

**Q: How many checkpoints are kept?**  
A: Last 3 temporary checkpoints, all production backups.

**Q: Can I delete old backups?**  
A: Yes, manually delete `production-backup-*` directories when you're sure.

---

**This is a much safer approach than the old auto-delete system! 🎉**
