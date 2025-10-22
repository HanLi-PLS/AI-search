# Security Group Configuration - Detailed Guide

## 🔐 What is a Security Group?

A **Security Group** is like a firewall for your EC2 instance. It controls what network traffic can reach your server.

Think of it as a security guard at the door:
- **Inbound rules**: What traffic can ENTER your server
- **Outbound rules**: What traffic can LEAVE your server (usually allow all)

**Without proper security group settings, you won't be able to:**
- ❌ Connect to your EC2 instance via SSH
- ❌ Access your web application
- ❌ Set up future features like HTTPS

---

## 🔌 Ports Explained

### What is a Port?

A **port** is like a door number on your server. Different services use different ports.

**Analogy:**
```
Your EC2 Instance = An apartment building
Ports = Different apartment numbers
Services = Residents in each apartment

Port 22  = SSH service lives here (remote access)
Port 8000 = AI Search app lives here (web application)
Port 80  = Future Nginx lives here (optional)
```

### Why We Need Each Port

#### **Port 22 - SSH (Secure Shell)**
```
Purpose:     Remote terminal access to your EC2 instance
Who needs:   YOU (to connect and manage the server)
Security:    Should ONLY allow YOUR IP address
Protocol:    TCP

Example usage:
$ ssh -i ai-search-key.pem ec2-user@YOUR-EC2-IP
  ↑ This connection uses port 22
```

**⚠️ CRITICAL SECURITY:**
- Set source to "My IP" (not "Anywhere")
- If set to "Anywhere", hackers can try to access your server
- AWS auto-detects your current IP address

---

#### **Port 8000 - AI Search Application**
```
Purpose:     Web access to your AI Document Search app
Who needs:   EVERYONE who will use the application
Security:    Usually "Anywhere" (0.0.0.0/0) for web apps
Protocol:    TCP

Example usage:
http://YOUR-EC2-IP:8000
                   ↑ This is the port number
```

**Why "Anywhere" (0.0.0.0/0)?**
- You want users to access from home, office, mobile, etc.
- Different locations have different IP addresses
- Setting to "Anywhere" allows access from any IP

**Is this secure?**
- ✅ YES - The application itself has no built-in authentication yet
- ✅ Only this specific port is open, not the whole server
- ✅ The application doesn't expose system files
- ⏳ You can add user authentication later if needed

---

#### **Port 80 - HTTP (Optional for now)**
```
Purpose:     Standard web traffic (for future Nginx setup)
Who needs:   Users (when you set up reverse proxy)
Security:    "Anywhere" (0.0.0.0/0)
Protocol:    TCP

Why add it now?
- So you don't have to modify security group later
- Allows future setup of Nginx (http://YOUR-IP instead of http://YOUR-IP:8000)
- Port 80 is the default HTTP port (no :80 needed in URLs)
```

**Future setup (optional):**
```
Without Nginx:  http://54.123.45.67:8000  ← ugly, need to remember port
With Nginx:     http://54.123.45.67       ← clean, professional
```

---

## 📝 Step-by-Step: Configure Security Group During EC2 Creation

### When You're Creating Your EC2 Instance

**You'll see this section:**

```
┌──────────────────────────────────────────────────┐
│ Network settings                                  │
├──────────────────────────────────────────────────┤
│ [ ] Create security group (selected)             │
│ [✓] Allow SSH traffic from                       │
│     └─ [My IP ▼]                                 │
│                                                   │
│ Edit ← CLICK THIS BUTTON                         │
└──────────────────────────────────────────────────┘
```

### Step 1: Click "Edit" Button

This expands the security group settings.

### Step 2: Fill in Basic Info

```
Security group name:     ai-search-sg
Description:            Security group for AI Document Search application
```

**Why these names?**
- Makes it easy to identify later
- Can have multiple security groups, this name helps

### Step 3: Configure Inbound Rules

You'll see a table like this:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Inbound security group rules                                        │
├──────┬──────────┬─────────┬─────────────────┬─────────────────────┤
│ Type │ Protocol │ Port    │ Source type     │ Source              │
├──────┼──────────┼─────────┼─────────────────┼─────────────────────┤
│ SSH  │ TCP      │ 22      │ My IP           │ 203.0.113.0/32     │
└──────┴──────────┴─────────┴─────────────────┴─────────────────────┘

[+ Add security group rule]  ← Click this to add more rules
```

**Rule 1 is already there (SSH). Now add Rules 2 and 3:**

---

### Rule 1: SSH (Already Configured)

```
Type:          SSH
Protocol:      TCP
Port range:    22
Source type:   My IP
Source:        (Auto-filled with your current IP, e.g., 203.0.113.0/32)
Description:   SSH access from my computer
```

✅ **Leave this as-is**

**What this means:**
- Only computers from YOUR current IP address can SSH into the server
- The `/32` means exactly this one IP address
- If your home/office IP changes, you'll need to update this

---

### Rule 2: Application Port (ADD THIS)

**Click "Add security group rule"**

```
Type:          Custom TCP
Protocol:      TCP
Port range:    8000
Source type:   Anywhere-IPv4
Source:        0.0.0.0/0  (Auto-filled when you select Anywhere-IPv4)
Description:   AI Search web application
```

**Fill in like this:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ Type:          [Custom TCP ▼]                                       │
│ Protocol:      [TCP ▼]                                              │
│ Port range:    [8000]                                               │
│ Source type:   [Anywhere-IPv4 ▼]                                    │
│ Source:        [0.0.0.0/0] ← Auto-filled                           │
│ Description:   [AI Search web application]                          │
└─────────────────────────────────────────────────────────────────────┘
```

**What this means:**
- `0.0.0.0/0` = Any IP address can connect
- `/0` means all IP addresses (no restrictions)
- This allows users from anywhere to access your app

---

### Rule 3: HTTP Port (ADD THIS - Optional but Recommended)

**Click "Add security group rule" again**

```
Type:          HTTP
Protocol:      TCP
Port range:    80
Source type:   Anywhere-IPv4
Source:        0.0.0.0/0
Description:   HTTP for future Nginx setup
```

**OR use the shortcut:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ Type:          [HTTP ▼]  ← Select this and it auto-fills!          │
│ Protocol:      [TCP]                                                │
│ Port range:    [80]                                                 │
│ Source type:   [Anywhere-IPv4 ▼]                                    │
│ Source:        [0.0.0.0/0]                                          │
│ Description:   [HTTP for future Nginx setup]                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

### Final Security Group Configuration

**Your complete inbound rules should look like this:**

```
┌────────────────────────────────────────────────────────────────────────┐
│ Inbound security group rules                                           │
├──────┬──────────┬──────┬─────────────────┬──────────────────────────┤
│ Type │ Protocol │ Port │ Source          │ Description              │
├──────┼──────────┼──────┼─────────────────┼──────────────────────────┤
│ SSH  │ TCP      │ 22   │ 203.0.113.0/32  │ SSH access               │
├──────┼──────────┼──────┼─────────────────┼──────────────────────────┤
│ TCP  │ TCP      │ 8000 │ 0.0.0.0/0       │ AI Search application    │
├──────┼──────────┼──────┼─────────────────┼──────────────────────────┤
│ HTTP │ TCP      │ 80   │ 0.0.0.0/0       │ Future Nginx setup       │
└──────┴──────────┴──────┴─────────────────┴──────────────────────────┘
```

✅ **Perfect! This is what you need.**

---

## 🔍 Understanding Source Formats

### What does `0.0.0.0/0` mean?

```
0.0.0.0/0  = Anywhere (all IP addresses)
  ↑     ↑
  │     │
  │     └─ /0 means "no restrictions" (all 32 bits can vary)
  │
  └─ Starting IP address
```

### What does `203.0.113.0/32` mean?

```
203.0.113.0/32  = One specific IP address
           ↑
           └─ /32 means "exact match" (no bits can vary)
```

### Common CIDR Notations

```
0.0.0.0/0      = Anywhere (the entire internet)
203.0.113.0/32 = Single IP: 203.0.113.0
10.0.0.0/24    = Range: 10.0.0.0 to 10.0.0.255 (256 addresses)
10.0.0.0/16    = Range: 10.0.0.0 to 10.0.255.255 (65,536 addresses)
```

---

## 🛡️ Security Best Practices

### ✅ DO:

1. **SSH (Port 22)**
   - ✅ Set to "My IP" (restricts to your location)
   - ✅ Update if your IP changes
   - ✅ Use strong key pairs (.pem files)

2. **Application (Port 8000)**
   - ✅ Set to "Anywhere" for public access
   - ✅ Add authentication in application later if needed
   - ✅ Monitor access logs

3. **General**
   - ✅ Only open ports you need
   - ✅ Use descriptive names
   - ✅ Review rules periodically

### ❌ DON'T:

1. **SSH (Port 22)**
   - ❌ NEVER set SSH to "Anywhere" (0.0.0.0/0)
   - ❌ Don't share your .pem key file
   - ❌ Don't use weak passwords (use key-based auth)

2. **Random Ports**
   - ❌ Don't open all ports (0-65535)
   - ❌ Don't allow unnecessary services
   - ❌ Don't leave default/test rules

---

## 🔧 Common Issues & Solutions

### Issue 1: "Can't connect via SSH"

**Error:**
```
ssh: connect to host XX.XXX.XXX.XX port 22: Connection refused
```

**Solution:**
```
Check security group:
1. Port 22 must be open
2. Source must include your current IP
3. Your IP may have changed (work vs home)
```

**Fix:**
1. EC2 Console → Security Groups
2. Select `ai-search-sg`
3. Edit inbound rules → Update SSH source to "My IP"

---

### Issue 2: "Can't access application on port 8000"

**Error:**
```
Browser: "This site can't be reached"
```

**Solution:**
```
Check:
1. Port 8000 is open in security group
2. Source is 0.0.0.0/0 (Anywhere)
3. Application is actually running: docker-compose ps
```

**Fix:**
1. Verify security group allows port 8000
2. Check application is running: `sudo docker-compose ps`

---

### Issue 3: "SSH works from home but not office"

**Cause:**
```
Your SSH rule is set to specific IP (home IP)
Office has different IP
```

**Solution Option 1 (Recommended):**
```
Add a second SSH rule with your office IP:
- Rule 1: SSH from home IP
- Rule 2: SSH from office IP
```

**Solution Option 2 (Less Secure):**
```
Change SSH source to IP range that covers both:
- Example: If home is 203.0.113.5 and office is 203.0.113.200
- Use: 203.0.113.0/24 (covers 203.0.113.0 to 203.0.113.255)
```

**Solution Option 3 (Not Recommended):**
```
Set SSH to "Anywhere" (0.0.0.0/0)
⚠️ Less secure - hackers can attempt to connect
Only use if you have:
- Strong key pair authentication
- No password auth enabled
- Fail2ban or similar protection
```

---

## 📋 Quick Checklist

Before launching your EC2 instance, verify:

- [ ] Security group name: `ai-search-sg`
- [ ] SSH (Port 22) - Source: My IP
- [ ] Custom TCP (Port 8000) - Source: Anywhere (0.0.0.0/0)
- [ ] HTTP (Port 80) - Source: Anywhere (0.0.0.0/0)
- [ ] Each rule has a description
- [ ] No extra ports are open unnecessarily

---

## 🎓 Advanced: What You're NOT Opening

**Your security group does NOT allow:**

```
✅ Allowed (Inbound):
- SSH (22) from your IP
- HTTP (8000) from anywhere
- HTTP (80) from anywhere

❌ Blocked (Everything else):
- Port 3389 (Windows RDP)
- Port 3306 (MySQL)
- Port 5432 (PostgreSQL)
- Port 6333 (Qdrant) ← Internal only
- All other ports

This is GOOD! Only open what you need.
```

**Note:** Qdrant (port 6333) is accessible only from within the EC2 instance, not from the internet. This is secure by default.

---

## 🔄 Modifying Security Group After Creation

**Need to change security group settings later?**

**Method 1: During Instance Running**
1. EC2 Console → Instances
2. Select your instance
3. Security tab → Click security group name
4. Actions → Edit inbound rules
5. Add/modify/delete rules
6. Save rules (takes effect immediately)

**Method 2: Create New Security Group**
1. EC2 Console → Security Groups
2. Create new security group
3. Configure rules
4. EC2 → Select instance → Actions → Security → Change security groups
5. Select new group

---

## 🎯 Summary: What Each Port Does

| Port | Service | Who Can Access | Why |
|------|---------|----------------|-----|
| **22** | SSH | Your IP only | Remote server management |
| **8000** | AI Search App | Anyone | Public web application |
| **80** | HTTP/Nginx | Anyone | Future clean URLs |

---

## 💡 Visual Example: Complete Flow

```
User Types: http://54.123.45.67:8000
                           ↓
          Internet (0.0.0.0/0 allowed on port 8000)
                           ↓
          AWS Security Group (checks: port 8000 open?)
                           ↓
                    ✅ ALLOWED
                           ↓
               EC2 Instance (your server)
                           ↓
            FastAPI app listening on port 8000
                           ↓
                   Returns web page
                           ↓
                  User sees AI Search UI


You Type: ssh -i key.pem ec2-user@54.123.45.67
                           ↓
              Internet (from your IP)
                           ↓
        AWS Security Group (checks: your IP on port 22?)
                           ↓
                    ✅ ALLOWED
                           ↓
               EC2 Instance (your server)
                           ↓
                SSH service on port 22
                           ↓
             Terminal access to server
```

---

## ❓ FAQ

**Q: Why not just allow all ports?**
A: Security! Only open what you need. Each open port is a potential entry point.

**Q: Can I change the application port from 8000 to something else?**
A: Yes, but you'd need to:
1. Change security group to new port
2. Change docker-compose.yml port mapping
3. Update application config

**Q: Is port 8000 secure?**
A: The port itself is just a number. Security comes from:
- Application authentication (can be added later)
- HTTPS/SSL (can be added with Nginx)
- Only exposing necessary services

**Q: What if I forget to add a port?**
A: No problem! You can add it anytime:
- EC2 Console → Security Groups → Edit inbound rules
- Changes take effect immediately

**Q: Can I add port 443 for HTTPS now?**
A: Yes! Add:
- Type: HTTPS
- Protocol: TCP
- Port: 443
- Source: Anywhere (0.0.0.0/0)

---

## 🚀 Ready to Create Your Instance?

Now you understand security groups!

**Next step**: Follow [CREATE_EC2_INSTANCE.md](CREATE_EC2_INSTANCE.md) and when you get to Step 5 (Network Settings), you'll know exactly what to do!

**Quick reference for Step 5:**
1. Click "Edit" on Network Settings
2. Name: `ai-search-sg`
3. Add 3 inbound rules:
   - SSH (22) - My IP
   - Custom TCP (8000) - Anywhere
   - HTTP (80) - Anywhere
4. Continue with instance creation

---

**Questions about security groups?** Ask me! 🔐
