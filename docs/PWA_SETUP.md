# Progressive Web App (PWA) Setup Guide

CropIoT is now a Progressive Web App that can be installed on your PC, phone, or tablet for a native app-like experience.

## What is a PWA?

A Progressive Web App works like a regular website but can be installed on your device and works offline. Benefits include:

- **Install on Desktop/Mobile**: Add to home screen or install like a native app
- **Offline Access**: View cached data even without internet
- **Fast Loading**: Cached resources load instantly
- **Native Feel**: Full-screen mode without browser UI
- **Auto Updates**: Always get the latest version

## Installation Instructions

### On Desktop (Windows/Mac/Linux)

1. **Open CropIoT in Chrome, Edge, or Brave**
   - Navigate to your CropIoT URL (e.g., `http://localhost:3000`)

2. **Install the App**
   - Look for the install icon in the address bar (⊕ or computer icon)
   - Click it and select "Install"
   - Or click the three dots menu → "Install CropIoT"

3. **Launch the App**
   - Find CropIoT in your applications menu
   - Or create a desktop shortcut
   - Opens in its own window without browser UI

### On Mobile (Android/iOS)

#### Android (Chrome)
1. Open CropIoT in Chrome
2. Tap the three dots menu (⋮)
3. Select "Add to Home screen"
4. Tap "Add" to confirm
5. Find the CropIoT icon on your home screen

#### iOS (Safari)
1. Open CropIoT in Safari
2. Tap the Share button (□↑)
3. Scroll down and tap "Add to Home Screen"
4. Tap "Add" to confirm
5. Find the CropIoT icon on your home screen

## Features

### Offline Functionality

The PWA caches essential resources so you can:
- View the dashboard even without internet
- See previously loaded sensor data
- Access the map (with cached tiles)
- Navigate between pages

**Note**: Real-time data updates require internet connection.

### App-Like Experience

- **Full Screen**: No browser address bar or tabs
- **Fast Launch**: Opens instantly from your desktop/home screen
- **Native Notifications**: (Coming soon) Get alerts for sensor issues
- **Background Sync**: (Coming soon) Sync data when connection returns

### Automatic Updates

The PWA automatically updates when you:
1. Close and reopen the app
2. Refresh the page
3. New version is deployed

No need to manually update or reinstall!

## Configuration Files

### manifest.json
Located at `public/manifest.json`, this defines:
- App name and description
- Icons and theme colors
- Display mode (standalone)
- Start URL

### Service Worker
Located at `public/sw.js`, this handles:
- Caching strategies
- Offline functionality
- Background sync
- Push notifications (future)

## Customization

### Change App Name
Edit `public/manifest.json`:
\`\`\`json
{
  "name": "Your Farm Name - CropIoT",
  "short_name": "YourFarm"
}
\`\`\`

### Change Theme Color
Edit `public/manifest.json`:
\`\`\`json
{
  "theme_color": "#16a34a",
  "background_color": "#ffffff"
}
\`\`\`

### Update Icons
Replace these files with your custom icons:
- `public/icon-192.jpg` (192x192 pixels)
- `public/icon-512.jpg` (512x512 pixels)

## Testing PWA Features

### Check PWA Status

1. **Chrome DevTools**
   - Open DevTools (F12)
   - Go to "Application" tab
   - Check "Manifest" section
   - Check "Service Workers" section

2. **Lighthouse Audit**
   - Open DevTools (F12)
   - Go to "Lighthouse" tab
   - Select "Progressive Web App"
   - Click "Generate report"
   - Aim for 100% PWA score

### Test Offline Mode

1. Open CropIoT in browser
2. Open DevTools (F12)
3. Go to "Network" tab
4. Check "Offline" checkbox
5. Refresh the page
6. App should still load with cached data

## Troubleshooting

### App Won't Install

**Issue**: No install prompt appears

**Solutions**:
- Use Chrome, Edge, or Brave (Safari has limited PWA support)
- Ensure you're on HTTPS (or localhost for development)
- Check manifest.json is valid
- Clear browser cache and try again

### Service Worker Not Registering

**Issue**: Offline mode doesn't work

**Solutions**:
1. Check browser console for errors
2. Verify `public/sw.js` exists
3. Clear service workers:
   - DevTools → Application → Service Workers
   - Click "Unregister" and refresh

### Icons Not Showing

**Issue**: Default browser icon appears

**Solutions**:
- Ensure icon files exist in `public/` folder
- Check file names match manifest.json
- Icons must be PNG format
- Clear cache and reinstall

### Updates Not Applying

**Issue**: Old version still showing after update

**Solutions**:
1. Close all app windows
2. Clear browser cache
3. Unregister service worker
4. Reinstall the app

## Production Deployment

### HTTPS Required

PWAs require HTTPS in production. Options:

1. **Vercel** (Recommended)
   - Automatic HTTPS
   - Deploy with: `vercel --prod`

2. **Netlify**
   - Automatic HTTPS
   - Connect GitHub repo

3. **Custom Server**
   - Use Let's Encrypt for free SSL
   - Configure nginx/Apache with SSL

### Update Service Worker

When deploying updates:
1. Increment cache version in `sw.js`
2. Deploy new version
3. Users get update on next app launch

### Monitor PWA Performance

Use these tools:
- **Google Analytics**: Track PWA installs
- **Lighthouse CI**: Automated PWA audits
- **Workbox**: Advanced service worker features

## Advanced Features (Future)

### Push Notifications
Get alerts for:
- Sensor disconnections
- Disease detections
- Yield predictions ready
- Critical environmental conditions

### Background Sync
- Queue data updates when offline
- Sync automatically when connection returns
- Never lose sensor readings

### Periodic Background Sync
- Fetch latest data in background
- Keep dashboard up-to-date
- Even when app is closed

## Best Practices

1. **Keep It Fast**
   - Optimize images
   - Minimize JavaScript
   - Use code splitting

2. **Cache Wisely**
   - Cache static assets
   - Network-first for dynamic data
   - Clear old caches

3. **Test Offline**
   - Ensure core features work offline
   - Show clear offline indicators
   - Queue actions for later sync

4. **Update Regularly**
   - Deploy bug fixes quickly
   - Increment cache versions
   - Test updates before deploying

## Resources

- [PWA Documentation](https://web.dev/progressive-web-apps/)
- [Service Worker API](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [Web App Manifest](https://developer.mozilla.org/en-US/docs/Web/Manifest)
- [Workbox](https://developers.google.com/web/tools/workbox)

## Support

For issues or questions:
1. Check browser console for errors
2. Review this documentation
3. Test in Chrome DevTools
4. Check PWA compatibility: [What PWA Can Do Today](https://whatpwacando.today/)
