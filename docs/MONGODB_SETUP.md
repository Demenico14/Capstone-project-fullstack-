# MongoDB Setup Guide for CropIoT

This guide will help you set up MongoDB for storing system configuration that can be updated dynamically at runtime.

## Why MongoDB for Configuration?

- **Dynamic Updates**: Change settings without restarting the server
- **Centralized Storage**: All configuration in one place
- **Easy Management**: Update via the Settings page UI
- **Backup & Restore**: Easy to backup and restore configurations
- **Multi-Environment**: Different configs for dev, staging, production

## Setup Options

### Option 1: Local MongoDB (Development)

1. **Install MongoDB**
   \`\`\`bash
   # macOS
   brew tap mongodb/brew
   brew install mongodb-community
   brew services start mongodb-community

   # Ubuntu/Debian
   sudo apt-get install mongodb
   sudo systemctl start mongodb

   # Windows
   # Download from https://www.mongodb.com/try/download/community
   \`\`\`

2. **Add to .env.local**
   \`\`\`bash
   MONGODB_URI=mongodb://localhost:27017/cropiot
   \`\`\`

3. **Test Connection**
   \`\`\`bash
   mongosh
   use cropiot
   db.config.find()
   \`\`\`

### Option 2: MongoDB Atlas (Cloud - Recommended for Production)

1. **Create Free Account**
   - Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
   - Sign up for free tier (512MB storage)

2. **Create Cluster**
   - Click "Build a Database"
   - Choose "Shared" (Free tier)
   - Select region closest to you
   - Click "Create Cluster"

3. **Setup Database Access**
   - Go to "Database Access"
   - Click "Add New Database User"
   - Create username and password
   - Set permissions to "Read and write to any database"

4. **Setup Network Access**
   - Go to "Network Access"
   - Click "Add IP Address"
   - Choose "Allow Access from Anywhere" (0.0.0.0/0) for development
   - For production, add your server's IP

5. **Get Connection String**
   - Go to "Database" → "Connect"
   - Choose "Connect your application"
   - Copy the connection string
   - Replace `<password>` with your database user password

6. **Add to .env.local**
   \`\`\`bash
   MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/cropiot?retryWrites=true&w=majority
   \`\`\`

### Option 3: Docker (Easy Setup)

1. **Create docker-compose.yml**
   \`\`\`yaml
   version: '3.8'
   services:
     mongodb:
       image: mongo:latest
       container_name: cropiot-mongodb
       ports:
         - "27017:27017"
       environment:
         MONGO_INITDB_ROOT_USERNAME: admin
         MONGO_INITDB_ROOT_PASSWORD: password
         MONGO_INITDB_DATABASE: cropiot
       volumes:
         - mongodb_data:/data/db

   volumes:
     mongodb_data:
   \`\`\`

2. **Start MongoDB**
   \`\`\`bash
   docker-compose up -d
   \`\`\`

3. **Add to .env.local**
   \`\`\`bash
   MONGODB_URI=mongodb://admin:password@localhost:27017/cropiot?authSource=admin
   \`\`\`

## Install Dependencies

\`\`\`bash
npm install mongodb
\`\`\`

## Using the Configuration System

### 1. Update Settings via UI

1. Go to Settings page in your app
2. Update sensor coordinates, API endpoints, or satellite config
3. Click "Save to Database"
4. Changes apply immediately - no restart needed!

### 2. Access Config in Code

\`\`\`typescript
import { loadConfig } from '@/lib/config-loader'

// In any component or API route
const config = await loadConfig()
console.log(config.nodes) // Sensor coordinates
console.log(config.sensorApiUrl) // API endpoint
\`\`\`

### 3. API Endpoints

**GET /api/config** - Fetch current configuration
\`\`\`bash
curl http://localhost:3000/api/config
\`\`\`

**POST /api/config** - Update configuration
\`\`\`bash
curl -X POST http://localhost:3000/api/config \
  -H "Content-Type: application/json" \
  -d '{"nodes": {"Sensor_1": "-18.30252535,31.56415345"}}'
\`\`\`

## Database Structure

\`\`\`javascript
{
  _id: "system",
  data: {
    nodes: {
      Sensor_1: "-18.30252535,31.56415345",
      Sensor_2: "-18.303550260,31.56498854",
      Sensor_3: "-18.30284377,31.56554022"
    },
    farmCenter: {
      lat: -18.30252535,
      lng: 31.56415345
    },
    sensorApiUrl: "http://192.168.4.2:5000",
    diseaseApiUrl: "http://192.168.4.2:8000",
    yieldApiUrl: "http://192.168.4.2:9000",
    sentinelClientId: "your-client-id",
    sentinelInstanceId: "your-instance-id",
    geeServiceAccount: "your-service-account@project.iam.gserviceaccount.com"
  },
  updatedAt: ISODate("2025-01-28T10:30:00Z")
}
\`\`\`

## Backup & Restore

### Backup
\`\`\`bash
mongodump --uri="mongodb://localhost:27017/cropiot" --out=./backup
\`\`\`

### Restore
\`\`\`bash
mongorestore --uri="mongodb://localhost:27017/cropiot" ./backup/cropiot
\`\`\`

## Troubleshooting

### Connection Issues

1. **Check MongoDB is running**
   \`\`\`bash
   # Local
   mongosh
   
   # Docker
   docker ps | grep mongodb
   \`\`\`

2. **Verify connection string**
   - Check username/password
   - Check database name
   - Check IP whitelist (Atlas)

3. **Check firewall**
   \`\`\`bash
   # Allow MongoDB port
   sudo ufw allow 27017
   \`\`\`

### Common Errors

**"MongoServerError: Authentication failed"**
- Check username and password in connection string
- Verify user has correct permissions

**"MongoNetworkError: connect ECONNREFUSED"**
- MongoDB service not running
- Wrong host/port in connection string

**"MongooseServerSelectionError"**
- Network access not configured (Atlas)
- Firewall blocking connection

## Security Best Practices

1. **Never commit credentials**
   - Add `.env.local` to `.gitignore`
   - Use environment variables

2. **Use strong passwords**
   - At least 16 characters
   - Mix of letters, numbers, symbols

3. **Restrict network access**
   - Production: Whitelist specific IPs
   - Development: Use VPN or SSH tunnel

4. **Enable authentication**
   - Always use username/password
   - Consider certificate-based auth for production

5. **Regular backups**
   - Automated daily backups
   - Store backups securely off-site

## Next Steps

1. Set up MongoDB using one of the options above
2. Add `MONGODB_URI` to your `.env.local`
3. Restart your Next.js server
4. Go to Settings page and configure your system
5. Test that changes apply without restart

For more help, see:
- [MongoDB Documentation](https://docs.mongodb.com/)
- [MongoDB Atlas Tutorial](https://docs.atlas.mongodb.com/getting-started/)
- [Next.js with MongoDB](https://github.com/vercel/next.js/tree/canary/examples/with-mongodb)
\`\`\`

\`\`\`markdown file="" isHidden
