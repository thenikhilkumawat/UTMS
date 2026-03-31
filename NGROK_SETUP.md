# How to set up ngrok for phone access

## Step 1 - Download ngrok
Go to https://ngrok.com/download and download the Windows version.
Unzip it and put ngrok.exe in the uttam_tailors_v2 folder.

## Step 2 - Get free account (one time)
Go to https://dashboard.ngrok.com/signup and create a free account.
Copy your authtoken from https://dashboard.ngrok.com/get-started/your-authtoken

## Step 3 - Setup authtoken (one time only)
Open Command Prompt in the folder and run:
  ngrok config add-authtoken YOUR_TOKEN_HERE

## Step 4 - Start the app
Run START.bat to start the Flask app.

## Step 5 - Start ngrok
In a second Command Prompt window, run:
  ngrok http 5000

ngrok will show a URL like: https://abc123.ngrok-free.app
Use this URL on your phone to upload images via QR code!

## Notes
- The ngrok URL changes every time you restart ngrok (free plan)
- The app automatically adds ngrok headers so no browser warnings
- For QR image upload, use the ngrok HTTPS URL
