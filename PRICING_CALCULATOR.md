# AWS Pricing Calculator for AI Document Search

## 💰 Quick Cost Estimator

Use this to estimate your monthly costs based on usage patterns.

---

## Scenario 1: Production (24/7 Operation)

### Recommended Configuration
```
┌──────────────────────────────────────────────────┐
│ PRODUCTION SETUP (Always Running)                │
├──────────────────────────────────────────────────┤
│ EC2 Instance:      t3.medium                     │
│ Storage:           50 GB gp3                     │
│ Usage:             24/7 (730 hours/month)        │
└──────────────────────────────────────────────────┘

Monthly Cost Breakdown:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Service                  Calculation              Cost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EC2 t3.medium           $0.0416 × 730 hrs        $30.37
EBS gp3 (50 GB)         $0.08 × 50 GB            $4.00
Data Transfer Out       5 GB × $0.09/GB          $0.45
S3 Storage (50 GB)      50 GB × $0.023/GB        $1.15
S3 PUT Requests         10,000 × $0.005/1000     $0.05
S3 GET Requests         50,000 × $0.0004/1000    $0.02
Secrets Manager         1 secret                 $0.40
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL                                            $36.44/month
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Additional Costs:
- OpenAI API: Variable (depends on usage)
  - o4-mini: ~$0.15 per 1M input tokens
  - ~$0.60 per 1M output tokens
  - Estimate: $10-50/month for moderate use
```

---

## Scenario 2: Budget Setup

### Minimal Configuration
```
┌──────────────────────────────────────────────────┐
│ BUDGET SETUP (24/7 with smaller instance)        │
├──────────────────────────────────────────────────┤
│ EC2 Instance:      t3.small                      │
│ Storage:           30 GB gp3                     │
│ Usage:             24/7 (730 hours/month)        │
└──────────────────────────────────────────────────┘

Monthly Cost Breakdown:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Service                  Calculation              Cost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EC2 t3.small            $0.0208 × 730 hrs        $15.18
EBS gp3 (30 GB)         $0.08 × 30 GB            $2.40
Data Transfer Out       3 GB × $0.09/GB          $0.27
S3 Storage (20 GB)      20 GB × $0.023/GB        $0.46
S3 Requests             Minimal                  $0.03
Secrets Manager         1 secret                 $0.40
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL                                            $18.74/month
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ Caveat: May be slower for large PDFs
```

---

## Scenario 3: Part-Time Development

### Development/Testing (8 hrs/day, 5 days/week)
```
┌──────────────────────────────────────────────────┐
│ DEVELOPMENT SETUP (Part-time usage)              │
├──────────────────────────────────────────────────┤
│ EC2 Instance:      t3.medium                     │
│ Storage:           50 GB gp3                     │
│ Usage:             8 hrs/day × 22 days = 176 hrs│
└──────────────────────────────────────────────────┘

Monthly Cost Breakdown:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Service                  Calculation              Cost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EC2 t3.medium           $0.0416 × 176 hrs        $7.32
EBS gp3 (50 GB)         $0.08 × 50 GB (always)   $4.00
Data Transfer Out       1 GB × $0.09/GB          $0.09
S3 Storage (10 GB)      10 GB × $0.023/GB        $0.23
S3 Requests             Minimal                  $0.02
Secrets Manager         1 secret                 $0.40
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL                                            $12.06/month
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 Pro Tip: Stop instance when not in use to save EC2 costs!
```

---

## Scenario 4: FREE TIER (First 12 Months)

### New AWS Account Benefits
```
┌──────────────────────────────────────────────────┐
│ FREE TIER (New AWS accounts only)                │
├──────────────────────────────────────────────────┤
│ EC2 Instance:      t3.micro (NOT t3.medium!)     │
│ Storage:           30 GB EBS                     │
│ Duration:          First 12 months               │
└──────────────────────────────────────────────────┘

What's FREE (per month for 12 months):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Service                  Free Tier Limit          Value
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EC2 t3.micro            750 hours/month          ~$6.50
EBS Storage             30 GB                    $2.40
Data Transfer Out       15 GB                    $1.35
S3 Storage              5 GB                     $0.12
S3 PUT Requests         2,000 requests           $0.01
S3 GET Requests         20,000 requests          $0.01
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL FREE                                       ~$10.39/month
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What You Still Pay:
- Secrets Manager: $0.40/month (not in free tier)
- OpenAI API: Variable based on usage

⚠️ Note: t3.micro is SLOW for this application
         Recommended only for initial testing
```

---

## 💡 Cost Optimization Strategies

### Strategy 1: Start Small, Scale Up
```
Month 1-2 (Testing):     t3.micro (FREE or $6.50)
Month 3+ (Production):   t3.medium ($30.37)

Savings: Test for free, then pay for production
```

### Strategy 2: Reserved Instances (1 Year Commitment)
```
t3.medium On-Demand:     $30.37/month
t3.medium Reserved:      $19.71/month (35% savings)

Annual Savings: ~$127
Upfront Cost: ~$180 (partial upfront)

💡 Worth it if you plan to run 24/7 for 1+ years
```

### Strategy 3: Stop When Not in Use
```
Scenario: Use 8 hours/day instead of 24/7

Cost if running 24/7:    $36.44/month
Cost if running 8hr/day: $12.06/month

Monthly Savings: $24.38 (67% reduction!)

How to stop:
AWS Console → EC2 → Select instance → Stop
(Storage costs remain, but EC2 compute stops)
```

### Strategy 4: Spot Instances (Advanced)
```
t3.medium On-Demand:     $0.0416/hour
t3.medium Spot:          ~$0.0125/hour (70% savings!)

Monthly Savings: ~$21

⚠️ Caveat: Can be interrupted with 2-min warning
Best for: Development, testing, non-critical workloads
```

---

## 🔥 OpenAI API Costs (Variable)

Your app uses **o4-mini** for PDF processing:

### PDF Processing Costs
```
o4-mini Pricing (as of 2025):
- Input:  ~$0.15 per 1M tokens
- Output: ~$0.60 per 1M tokens

Example Usage:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Scenario                 Tokens      Cost
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10 PDFs (20 pages each)  ~500K      ~$0.38
100 PDFs (20 pages each) ~5M        ~$3.75
1,000 PDFs              ~50M        ~$37.50
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 o4-mini is ~50% cheaper than gpt-4o
```

### Embedding Costs
```
We use sentence-transformers (local model):
Cost: $0 (runs on your EC2 instance)

Alternative (OpenAI embeddings):
- text-embedding-3-small: $0.02 per 1M tokens
- 10,000 documents ≈ 10M tokens ≈ $0.20
```

---

## 📊 Total Cost Examples

### Example 1: Small Business (Light Use)
```
Users: 5-10 people
Usage: 8 hours/day, 5 days/week
Documents: 50 PDFs/month

AWS Costs:
- EC2 (t3.medium, part-time): $7.32
- Storage: $4.00
- S3: $0.50
- Secrets Manager: $0.40
- Data Transfer: $0.20

OpenAI Costs:
- 50 PDFs × 20 pages: ~$1.90

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL: ~$14.32/month
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Example 2: Medium Organization (Heavy Use)
```
Users: 20-50 people
Usage: 24/7 availability
Documents: 500 PDFs/month

AWS Costs:
- EC2 (t3.medium, 24/7): $30.37
- Storage: $4.00
- S3: $2.00
- Secrets Manager: $0.40
- Data Transfer: $1.00

OpenAI Costs:
- 500 PDFs × 20 pages: ~$18.75

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL: ~$56.52/month
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Example 3: Large Enterprise
```
Users: 100+ people
Usage: 24/7 with high availability
Documents: 2,000 PDFs/month

AWS Costs:
- EC2 (t3.large, 24/7): $60.74
- Storage: $8.00
- S3: $5.00
- Secrets Manager: $0.40
- Data Transfer: $3.00

OpenAI Costs:
- 2,000 PDFs × 20 pages: ~$75.00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL: ~$152.14/month
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 At this scale, consider:
- Multi-AZ deployment
- Load balancer
- Auto-scaling
```

---

## 🎯 Quick Decision Guide

**Budget < $20/month?**
→ Use t3.small, stop when not in use

**Need 24/7 availability?**
→ Use t3.medium ($36/month)

**Just testing?**
→ Use t3.micro free tier (first 12 months)

**Heavy usage (100+ PDFs/day)?**
→ Use t3.large + consider Reserved Instances

**Want minimum cost?**
→ t3.medium part-time + stop overnight = ~$12/month

---

## 💳 Billing Tips

1. **Set up billing alerts**:
   - AWS Console → Billing → Budgets
   - Set alert at $50 to avoid surprises

2. **Monitor costs daily**:
   - AWS Console → Cost Explorer
   - Check spending trends

3. **Tag resources**:
   - Add tag "Project: AI-Search"
   - Track costs per project

4. **Review monthly**:
   - Check AWS bill on 1st of month
   - Look for unexpected charges

---

## 🆓 Ways to Reduce Costs

1. ✅ **Stop instance when not in use** (save ~70%)
2. ✅ **Use Reserved Instances** (save ~35% for 1-year)
3. ✅ **Right-size instance** (don't over-provision)
4. ✅ **Use local embeddings** (sentence-transformers, not OpenAI)
5. ✅ **Clean up old S3 files** (delete unused documents)
6. ✅ **Use o4-mini instead of gpt-4o** (already configured!)
7. ✅ **Set up lifecycle policies** (archive old S3 data to Glacier)

---

## 📞 Need Help Estimating?

Use AWS Pricing Calculator:
https://calculator.aws/

Input your specific usage patterns for accurate estimates.

---

**Bottom Line**:
- **Minimal setup**: ~$12-20/month
- **Production**: ~$35-40/month
- **Heavy use**: ~$60-150/month

All costs include AWS infrastructure + OpenAI API usage.
