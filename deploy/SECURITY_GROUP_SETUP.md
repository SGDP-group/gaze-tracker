# Security Group Configuration for EC2

## Required Security Group Rules

Create or update your EC2 security group to allow these inbound ports:

### Essential Rules
| Port | Protocol | Source | Description |
|------|----------|---------|-------------|
| 22   | TCP      | Your IP/32 | SSH access |
| 8002 | TCP      | 0.0.0.0/0 | API server |
| 5555 | TCP      | Your IP/32 | Flower monitoring (recommended) |
| 5555 | TCP      | 0.0.0.0/0 | Flower monitoring (less secure) |

### Optional Rules
| Port | Protocol | Source | Description |
|------|----------|---------|-------------|
| 80   | TCP      | 0.0.0.0/0 | HTTP (if using Nginx) |
| 443  | TCP      | 0.0.0.0/0 | HTTPS (if using SSL) |
| 6379 | TCP      | 127.0.0.1/32 | Redis (localhost only) |

## AWS CLI Commands

### Create Security Group
```bash
aws ec2 create-security-group \
    --group-name "focus-tracker-sg" \
    --description "Security group for Focus Tracker" \
    --vpc-id vpc-01622918a1cc82f6b \
    --region eu-north-1
```

### Add Inbound Rules
```bash
# SSH (replace YOUR_IP with your public IP)
aws ec2 authorize-security-group-ingress \
    --group-id "focus-tracker-sg" \
    --protocol tcp \
    --port 22 \
    --cidr YOUR_IP/32 \
    --region eu-north-1

# API Server
aws ec2 authorize-security-group-ingress \
    --group-id "focus-tracker-sg" \
    --protocol tcp \
    --port 8002 \
    --cidr 0.0.0.0/0 \
    --region eu-north-1

# Flower Monitoring (restrict to your IP for security)
aws ec2 authorize-security-group-ingress \
    --group-id "focus-tracker-sg" \
    --protocol tcp \
    --port 5555 \
    --cidr YOUR_IP/32 \
    --region eu-north-1
```

### Get Your Public IP
```bash
curl -s ifconfig.me
# Or
curl -s ipinfo.io/ip
```

## Console Instructions

1. Go to EC2 Console → Security Groups
2. Find the security group attached to your instance
3. Add inbound rules as shown above
4. Save the rules
