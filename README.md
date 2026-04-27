# Club Website

A small Flask club website with public visitor pages and a protected admin panel for members, notifications, academy programs, and image/video gallery uploads backed by MongoDB.

The public content structure is inspired by the Vivekananda Sangathan style: welcome/about, games and social activities, Vivekananda Utsav, admission/membership, gallery, members, notices, and contact.

## Project Structure

```text
club-website/
  app.py                 Flask routes and upload handling
  config.py              Environment-based app configuration
  utils/db.py            MongoDB client and database object
  templates/             Jinja HTML pages
    activities.html      Public games, sports, and social activities page
    utsav.html           Public Vivekananda Utsav page
    admission.html       Public admission, membership, and scholarship page
  static/css/style.css   Site styling
  static/uploads/        Uploaded images and videos
  .env.example           Environment variable template
```

## Admin Flow

Visitors can only view the public website. Uploading and editing content is available only after admin login at:

```text
http://127.0.0.1:5000/admin/login
```

Default development credentials are:

```text
username: admin
password: admin123
```

Change them in `.env` before sharing or deploying the site.

## MongoDB Setup

1. Install dependencies:

```powershell
venv\Scripts\pip install -r requirements.txt
```

2. Copy `.env.example` to `.env`.

3. For local MongoDB, keep:

```env
MONGO_URI=mongodb://localhost:27017/clubDB
MONGO_DB_NAME=clubDB
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-this-admin-password
```

4. For MongoDB Atlas, replace `MONGO_URI` with your Atlas connection string:

```env
MONGO_URI=mongodb+srv://USERNAME:PASSWORD@cluster-name.mongodb.net/clubDB?retryWrites=true&w=majority
MONGO_DB_NAME=clubDB
```

5. In Atlas, allow your current IP address in Network Access and create a database user with read/write permission.

6. Start the app:

```powershell
venv\Scripts\python app.py
```

The app will create collections automatically when you add members, upload gallery media, or submit contact messages.

## Cloudinary Uploads

Uploads use Cloudinary when `CLOUDINARY_URL` is set in `.env`:

```env
CLOUDINARY_URL=cloudinary://API_KEY:API_SECRET@CLOUD_NAME
```

Gallery files and section images/videos are uploaded to Cloudinary. MongoDB stores the Cloudinary URL, public id, and the text details. If `CLOUDINARY_URL` is empty, the app falls back to `static/uploads` for local development.

## PWA Support

The site includes a basic Progressive Web App setup:

```text
static/manifest.webmanifest
static/service-worker.js
static/icons/icon-192.svg
static/icons/icon-512.svg
```

Visitors can install the website from supported browsers. The service worker caches public pages and static assets, but skips admin routes and form submissions.
