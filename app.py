from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import os
from urllib.parse import parse_qs, quote, urlparse

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, flash, make_response, redirect, render_template, request, send_from_directory, session, url_for
from pymongo.errors import PyMongoError
from werkzeug.utils import secure_filename
import cloudinary
import cloudinary.uploader

from config import (
    ADMIN_PASSWORD,
    ADMIN_USERNAME,
    CLOUDINARY_URL,
    MAX_CONTENT_LENGTH,
    SECRET_KEY,
    SOCIAL_FACEBOOK,
    SOCIAL_WHATSAPP,
    SOCIAL_YOUTUBE,
    UPLOAD_FOLDER,
)
from utils.db import db

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["PREFERRED_URL_SCHEME"] = "https"

ALLOWED_EXTENSIONS = {
    "jpg": "image",
    "jpeg": "image",
    "png": "image",
    "gif": "image",
    "webp": "image",
    "mp4": "video",
    "mov": "video",
    "webm": "video",
}

Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

if CLOUDINARY_URL:
    cloudinary.config(cloudinary_url=CLOUDINARY_URL, secure=True)


def get_media_type(filename):
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return ALLOWED_EXTENSIONS.get(extension)


def save_uploaded_file(file, media_type):
    # Cloudinary is the main storage for uploaded images/videos.
    # MongoDB stores the returned URL and public_id, not the file bytes.
    if CLOUDINARY_URL:
        result = cloudinary.uploader.upload(
            file,
            folder="vivekananda-sangathan",
            resource_type="auto",
        )
        return {
            "filename": result.get("public_id"),
            "url": result.get("secure_url"),
            "public_id": result.get("public_id"),
            "storage": "cloudinary",
            "resource_type": result.get("resource_type", media_type),
        }

    # Local fallback for development if CLOUDINARY_URL is missing.
    filename = secure_filename(file.filename)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    stored_filename = f"{timestamp}-{filename}"
    path = Path(app.config["UPLOAD_FOLDER"]) / stored_filename
    file.save(path)
    return {
        "filename": stored_filename,
        "url": "",
        "public_id": "",
        "storage": "local",
        "resource_type": media_type,
    }


def asset_url(filename="", uploaded_url=""):
    # Templates use this for both Cloudinary and old local uploads.
    if uploaded_url:
        return uploaded_url
    if filename:
        return url_for("static", filename=f"uploads/{filename}")
    return ""


def external_url(endpoint, **values):
    values.setdefault("_external", True)
    values.setdefault("_scheme", "https")
    return url_for(endpoint, **values)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("admin_logged_in"):
            flash("Please log in as admin first.", "warning")
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped_view


def find_documents(collection, sort_field="created_at", fallback=None):
    try:
        cursor = collection.find()
        if sort_field:
            cursor = cursor.sort(sort_field, -1)
        return list(cursor)
    except PyMongoError:
        flash("MongoDB is not connected yet. Check your MONGO_URI and Mongo service.", "warning")
        return fallback or []


def insert_document(collection, document, success_message):
    try:
        collection.insert_one(document)
        flash(success_message, "success")
        return True
    except PyMongoError:
        flash("Could not save because MongoDB is not connected. Check your .env setup.", "danger")
        return False


def update_document(collection, document_id, document, success_message):
    try:
        collection.update_one({"_id": ObjectId(document_id)}, {"$set": document})
        flash(success_message, "success")
    except (PyMongoError, InvalidId):
        flash("Could not update this item.", "danger")


def delete_document(collection, document_id, success_message):
    try:
        collection.delete_one({"_id": ObjectId(document_id)})
        flash(success_message, "success")
    except (PyMongoError, InvalidId):
        flash("Could not delete this item.", "danger")


def delete_saved_media(document, filename_key="filename", public_id_key="public_id", storage_key="storage", resource_type_key="resource_type"):
    if document.get(storage_key) == "cloudinary" and document.get(public_id_key):
        cloudinary.uploader.destroy(document[public_id_key], resource_type=document.get(resource_type_key, "image"))
    elif document.get(filename_key):
        media_path = Path(app.config["UPLOAD_FOLDER"]) / secure_filename(document[filename_key])
        if media_path.exists():
            media_path.unlink()


def default_programs():
    return [
        {"title": "Cricket", "description": "Batting, bowling, fielding, and match awareness sessions."},
        {"title": "Football", "description": "Ball control, stamina, passing drills, and team play."},
        {"title": "Yoga", "description": "Flexibility, balance, breathing, and recovery routines."},
        {"title": "Karate", "description": "Self-control, strength, confidence, and focused movement."},
        {"title": "Chess", "description": "Strategy, tactics, critical thinking, and competitive play."},
        {"title": "Athletics", "description": "Running, jumping, throwing, and overall fitness training."},
        {"title": "Carrom", "description": "Precision, focus, and fun indoor game sessions."},
    ]


def default_sections():
    return {
        "home": {
            "label": "Home",
            "title": "Service, education, sports, and community growth.",
            "subtitle": "Social organization and sports academy",
            "body": "Vivekananda Sangathan supports children, youth, and families through education, sports training, cultural programs, health camps, and local welfare activities.",
        },
        "activities": {
            "label": "Activities",
            "title": "Community Activities",
            "subtitle": "Games, sports and social activities",
            "body": "Education, sports, health, culture, and service programs for the local community.",
        },
        "utsav": {
            "label": "Utsav",
            "title": "Festival and Cultural Programs",
            "subtitle": "Vivekananda Utsav",
            "body": "A public celebration of youth, service, culture, sports, and community values.",
        },
        "academy": {
            "label": "Academy",
            "title": "Academy",
            "subtitle": "Training",
            "body": "Programs designed for fitness, discipline, and long-term player growth.",
        },
        "admission": {
            "label": "Admission",
            "title": "Join Our Programs",
            "subtitle": "Admission, membership and scholarship",
            "body": "Visitors can review the details here and contact the office. Admin can publish notices for open admission dates.",
        },
        "gallery": {
            "label": "Gallery",
            "title": "Gallery",
            "subtitle": "Media",
            "body": "Watch match-day photos, training clips, event moments, and club memories.",
        },
        "projects": {
            "label": "Projects",
            "title": "Projects",
            "subtitle": "Community Work",
            "body": "Explore educational, service, cultural, and sports projects led by the organization.",
        },
        "members": {
            "label": "Members",
            "title": "Members",
            "subtitle": "Team",
            "body": "Meet the people helping the club run, train, and grow.",
        },
        "contact": {
            "label": "Contact",
            "title": "Contact Us",
            "subtitle": "Connect",
            "body": "Send a message for admission, practice timing, coaching, or events.",
        },
    }


def get_section(slug):
    default = default_sections()[slug].copy()
    default["slug"] = slug
    try:
        saved = db.sections.find_one({"slug": slug}) or {}
        default.update(saved)
    except PyMongoError:
        pass
    return default


def get_all_sections():
    return [get_section(slug) for slug in default_sections()]


def organization_profile():
    return {
        "name": "Vivekananda Sangathan",
        "address": "4 No Kataganj, P.O. Bedibhawan, Dist. Nadia, P.S. Kalyani, PIN 741250, West Bengal, India",
        "phone": "8910025263 / 9674271977",
        "email": "vibekanandasangathan02@gmail.com",
        "registration": "Registered non-profit social organization",
    }


def community_activities():
    return [
        {
            "title": "Free Education",
            "description": "Learning support for children and young people who need access to better guidance.",
        },
        {
            "title": "Library",
            "description": "A community reading space that supports students, members, and local families.",
        },
        {
            "title": "Sports Academy",
            "description": "Regular sports training in cricket, football, karate, badminton, athletics, and more.",
        },
        {
            "title": "Health Camps",
            "description": "Awareness programs, medical support camps, and public welfare initiatives.",
        },
        {
            "title": "Blood Donation",
            "description": "Volunteer-led donation and awareness drives for the wider community.",
        },
        {
            "title": "Cultural Programs",
            "description": "Celebration of national days, festivals, and community events throughout the year.",
        },
        {   
            "title": "Social Service",
            "description": "Community clean-up, support for local families, and social welfare activities."
        },
        {   
            "title": "Youth Development",
            "description": "Leadership, life skills, and personal growth programs for young members."
        },
        {   
            "title": "Community Events", 
            "description": "Organizing local events, competitions, and gatherings to foster community spirit."
        },
        {   
            "title": "Mentorship and Guidance", 
            "description": "Providing mentorship, career guidance, and support for students and young adults."
         },
         {   
            "title": "Health and Wellness",
            "description": "Promoting healthy lifestyles through fitness programs, nutrition awareness, and wellness workshops."
         },

    ]


def utsav_events():
    return [
        "Swami Vivekananda birthday celebration",
        "Seven-day community festival",
        "Cultural performances and youth programs",
        "Sports events and prize distribution",
        "Social awareness and service activities",
    ]


def member_sections():
    return {
        "administrative": "Administrative Section",
        "general": "General Member Section",
    }


def normalize_member_section(value):
    return value if value in member_sections() else "general"


def get_youtube_embed_url(value):
    if not value:
        return ""

    parsed = urlparse(value.strip())
    host = parsed.netloc.lower().replace("www.", "")
    path = parsed.path.strip("/")
    video_id = ""

    if host in {"youtube.com", "m.youtube.com"}:
        if path == "watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif path.startswith("embed/"):
            video_id = path.split("/", 1)[1]
        elif path.startswith("live/"):
            video_id = path.split("/", 1)[1]
        elif path == "shorts":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
    elif host == "youtu.be":
        video_id = path.split("/", 1)[0]

    if not video_id:
        return ""

    video_id = video_id.split("?")[0].split("&")[0].strip()
    if not video_id:
        return ""

    return f"https://www.youtube.com/embed/{video_id}"


def get_live_stream():
    data = {
        "title": "Live Streaming",
        "description": "Watch the latest live program directly on the website through YouTube Live.",
        "watch_url": "",
        "embed_url": "",
    }
    try:
        saved = db.settings.find_one({"key": "live_stream"}) or {}
        live_data = saved.get("data", {})
        data.update(live_data)
    except PyMongoError:
        pass
    return data


def get_featured_video():
    data = {
        "title": "Featured Video",
        "description": "Watch an important YouTube video directly on the website.",
        "videos": [],
    }
    try:
        saved = db.settings.find_one({"key": "featured_video"}) or {}
        video_data = saved.get("data", {})
        data.update(video_data)
    except PyMongoError:
        pass

    videos = data.get("videos") or []
    if not videos and data.get("watch_url") and data.get("embed_url"):
        videos = [{
            "watch_url": data.get("watch_url", ""),
            "embed_url": data.get("embed_url", ""),
        }]

    normalized_videos = []
    for item in videos[:5]:
        watch_url = (item or {}).get("watch_url", "").strip()
        embed_url = (item or {}).get("embed_url", "").strip()
        normalized_videos.append({
            "watch_url": watch_url,
            "embed_url": embed_url,
        })

    while len(normalized_videos) < 5:
        normalized_videos.append({"watch_url": "", "embed_url": ""})

    data["videos"] = normalized_videos
    return data


def get_donation_details():
    upi_id = "42263804680@sbi"
    payee_name = "Vivekananda Sangathan"
    upi_uri = f"upi://pay?pa={quote(upi_id)}&pn={quote(payee_name)}&cu=INR"
    return {
        "upi_id": upi_id,
        "payee_name": payee_name,
        "upi_uri": upi_uri,
        "qr_url": f"https://quickchart.io/qr?text={quote(upi_uri)}&size=320",
    }


def get_social_links():
    links = {
        "whatsapp": SOCIAL_WHATSAPP,
        "facebook": SOCIAL_FACEBOOK,
        "youtube": SOCIAL_YOUTUBE,
    }
    try:
        saved = db.settings.find_one({"key": "social_links"}) or {}
        links.update(saved.get("links", {}))
    except PyMongoError:
        pass
    return links


@app.context_processor
def inject_global_data():
    return {"social_links": get_social_links(), "asset_url": asset_url}


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory("static", "manifest.webmanifest", mimetype="application/manifest+json")


# Serve the AdSense ads.txt file from the site root for crawlers like Google.
@app.route("/ads.txt")
def ads_txt():
    return send_from_directory(app.root_path, "ads.txt", mimetype="text/plain")


@app.route("/robots.txt")
def robots():
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin",
        "Disallow: /admin/",
        "Disallow: /admin/login",
        f"Sitemap: {external_url('sitemap')}",
    ]
    response = make_response("\n".join(lines) + "\n")
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response


@app.route("/sitemap.xml")
def sitemap():
    pages = [
        external_url("home"),
        external_url("gallery"),
        external_url("projects"),
        external_url("activities"),
        external_url("utsav"),
        external_url("academy"),
        external_url("admission"),
        external_url("members"),
        external_url("contact"),
    ]
    xml = render_template("sitemap.xml", pages=pages, lastmod=datetime.now(timezone.utc).date().isoformat())
    response = make_response(xml)
    response.headers["Content-Type"] = "application/xml; charset=utf-8"
    return response


@app.route("/service-worker.js")
def service_worker():
    response = make_response(send_from_directory("static", "service-worker.js", mimetype="application/javascript"))
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


# ---------------- HOME ----------------
@app.route("/")
def home():
    notifications = find_documents(db.notifications, fallback=[])
    return render_template(
        "home.html",
        notifications=notifications[:3],
        profile=organization_profile(),
        activities=community_activities()[:3],
        live_stream=get_live_stream(),
        featured_video=get_featured_video(),
        donation=get_donation_details(),
        section=get_section("home"),
    )


@app.route("/activities")
def activities():
    return render_template("activities.html", activities=community_activities(), section=get_section("activities"))


@app.route("/utsav")
def utsav():
    return render_template("utsav.html", events=utsav_events(), section=get_section("utsav"))


@app.route("/admission")
def admission():
    return render_template("admission.html", profile=organization_profile(), section=get_section("admission"))

# ---------------- GALLERY ----------------
@app.route("/gallery")
def gallery():
    media = find_documents(db.gallery)
    return render_template("gallery.html", media=media, section=get_section("gallery"))


@app.route("/projects")
def projects():
    items = find_documents(db.projects, sort_field="project_date")
    return render_template("projects.html", projects=items, section=get_section("projects"))


@app.route("/admin/gallery/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Please choose an image or video to upload.", "warning")
        return redirect(url_for("admin"))

    media_type = get_media_type(file.filename)

    if not media_type:
        flash("Only JPG, PNG, GIF, WEBP, MP4, MOV, and WEBM files are allowed.", "danger")
        return redirect(url_for("admin"))

    upload_result = save_uploaded_file(file, media_type)

    insert_document(db.gallery, {
        "filename": upload_result["filename"],
        "url": upload_result["url"],
        "public_id": upload_result["public_id"],
        "storage": upload_result["storage"],
        "resource_type": upload_result["resource_type"],
        "media_type": media_type,
        "title": request.form.get("title", "").strip(),
        "location": request.form.get("location", "").strip(),
        "category": request.form.get("category", "").strip(),
        "created_at": datetime.now(timezone.utc),
    }, "Media uploaded successfully.")
    return redirect(url_for("admin"))

# ---------------- MEMBERS ----------------
@app.route("/members")
def members():
    data = find_documents(db.members)
    administrative_members = [m for m in data if normalize_member_section(m.get("member_section")) == "administrative"]
    general_members = [m for m in data if normalize_member_section(m.get("member_section")) == "general"]
    return render_template(
        "members.html",
        members=data,
        administrative_members=administrative_members,
        general_members=general_members,
        section=get_section("members"),
    )

# ---------------- ACADEMY ----------------
@app.route("/academy")
def academy():
    programs = find_documents(db.programs)
    if not programs:
        programs = default_programs()
    return render_template("academy.html", programs=programs, section=get_section("academy"))

# ---------------- CONTACT ----------------
@app.route("/donate", methods=["POST"])
def donate():
    insert_document(db.donations, {
        "name": request.form["name"].strip(),
        "phone": request.form["phone"].strip(),
        "email": request.form.get("email", "").strip(),
        "amount": request.form["amount"].strip(),
        "transaction_ref": request.form["transaction_ref"].strip(),
        "note": request.form.get("note", "").strip(),
        "status": "submitted",
        "payment_method": "UPI QR",
        "upi_id": get_donation_details()["upi_id"],
        "created_at": datetime.now(timezone.utc),
    }, "Thank you. Your donation details have been submitted successfully.")
    return redirect(url_for("home") + "#donate")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        insert_document(db.queries, {
            "name": request.form["name"],
            "email": request.form.get("email", ""),
            "message": request.form["message"],
            "created_at": datetime.now(timezone.utc),
        }, "Thanks. We will contact you soon.")
        return redirect(url_for("contact"))
    return render_template("contact.html", profile=organization_profile(), section=get_section("contact"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            flash("Welcome back, admin.", "success")
            return redirect(url_for("admin"))

        flash("Invalid admin username or password.", "danger")

    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
@login_required
def admin_logout():
    session.clear()
    flash("Admin logged out.", "success")
    return redirect(url_for("home"))


# ---------------- ADMIN PANEL ----------------
@app.route("/admin")
@login_required
def admin():
    members = find_documents(db.members)
    notifications = find_documents(db.notifications)
    queries = find_documents(db.queries)
    donations = find_documents(db.donations)
    media = find_documents(db.gallery)
    projects = find_documents(db.projects, sort_field="project_date")
    programs = find_documents(db.programs)
    sections = get_all_sections()
    return render_template(
        "admin.html",
        members=members,
        notifications=notifications,
        queries=queries,
        donations=donations,
        media=media,
        projects=projects,
        programs=programs,
        sections=sections,
        member_sections=member_sections(),
        live_stream=get_live_stream(),
        featured_video=get_featured_video(),
        social_links=get_social_links(),
    )


@app.route("/admin/queries/<query_id>/read", methods=["POST"])
@login_required
def mark_query_read(query_id):
    update_document(db.queries, query_id, {
        "status": "read",
        "read_at": datetime.now(timezone.utc),
    }, "Message marked as read.")
    return redirect(url_for("admin"))


@app.route("/admin/queries/<query_id>/delete", methods=["POST"])
@login_required
def delete_query(query_id):
    delete_document(db.queries, query_id, "Message deleted successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/donations/<donation_id>/verify", methods=["POST"])
@login_required
def verify_donation(donation_id):
    update_document(db.donations, donation_id, {
        "status": "verified",
        "verified_at": datetime.now(timezone.utc),
    }, "Donation marked as verified.")
    return redirect(url_for("admin"))


@app.route("/admin/sections/<slug>", methods=["POST"])
@login_required
def update_section(slug):
    if slug not in default_sections():
        flash("Unknown section.", "danger")
        return redirect(url_for("admin"))

    section_image = request.files.get("image")
    document = {
        "slug": slug,
        "label": default_sections()[slug]["label"],
        "title": request.form["title"].strip(),
        "subtitle": request.form["subtitle"].strip(),
        "body": request.form["body"].strip(),
        "updated_at": datetime.now(timezone.utc),
    }

    if section_image and section_image.filename:
        if get_media_type(section_image.filename) != "image":
            flash("Section image must be JPG, PNG, GIF, or WEBP.", "danger")
            return redirect(url_for("admin"))
        upload_result = save_uploaded_file(section_image, "image")
        document["image"] = upload_result["filename"]
        document["image_url"] = upload_result["url"]
        document["image_public_id"] = upload_result["public_id"]
        document["image_storage"] = upload_result["storage"]

    about_image = request.files.get("about_image")
    if slug == "home" and about_image and about_image.filename:
        if get_media_type(about_image.filename) != "image":
            flash("Welcome image must be JPG, PNG, GIF, or WEBP.", "danger")
            return redirect(url_for("admin"))
        upload_result = save_uploaded_file(about_image, "image")
        document["about_image"] = upload_result["filename"]
        document["about_image_url"] = upload_result["url"]
        document["about_image_public_id"] = upload_result["public_id"]
        document["about_image_storage"] = upload_result["storage"]

    try:
        db.sections.update_one({"slug": slug}, {"$set": document}, upsert=True)
        flash(f"{document['label']} section updated successfully.", "success")
    except PyMongoError:
        flash("Could not save section content. Check MongoDB connection.", "danger")

    return redirect(url_for("admin"))


@app.route("/admin/sections/<slug>/image/delete", methods=["POST"])
@login_required
def delete_section_image(slug):
    if slug not in default_sections():
        flash("Unknown section.", "danger")
        return redirect(url_for("admin"))

    try:
        section = db.sections.find_one({"slug": slug}) or {}
        delete_saved_media(
            section,
            filename_key="image",
            public_id_key="image_public_id",
            storage_key="image_storage",
            resource_type_key="image_resource_type",
        )
        db.sections.update_one(
            {"slug": slug},
            {
                "$unset": {
                    "image": "",
                    "image_url": "",
                    "image_public_id": "",
                    "image_storage": "",
                    "image_resource_type": "",
                }
            },
        )
        flash("Section image deleted successfully.", "success")
    except PyMongoError:
        flash("Could not delete section image. Check MongoDB connection.", "danger")

    return redirect(url_for("admin"))


@app.route("/admin/sections/<slug>/about-image/delete", methods=["POST"])
@login_required
def delete_section_about_image(slug):
    if slug != "home":
        flash("Unknown section image.", "danger")
        return redirect(url_for("admin"))

    try:
        section = db.sections.find_one({"slug": slug}) or {}
        delete_saved_media(
            section,
            filename_key="about_image",
            public_id_key="about_image_public_id",
            storage_key="about_image_storage",
            resource_type_key="about_image_resource_type",
        )
        db.sections.update_one(
            {"slug": slug},
            {
                "$unset": {
                    "about_image": "",
                    "about_image_url": "",
                    "about_image_public_id": "",
                    "about_image_storage": "",
                    "about_image_resource_type": "",
                }
            },
        )
        flash("Welcome section image deleted successfully.", "success")
    except PyMongoError:
        flash("Could not delete welcome section image. Check MongoDB connection.", "danger")

    return redirect(url_for("admin"))


@app.route("/admin/social-links", methods=["POST"])
@login_required
def update_social_links():
    links = {
        "whatsapp": request.form.get("whatsapp", "").strip(),
        "facebook": request.form.get("facebook", "").strip(),
        "youtube": request.form.get("youtube", "").strip(),
    }
    try:
        db.settings.update_one(
            {"key": "social_links"},
            {"$set": {"key": "social_links", "links": links, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        flash("Social media links updated successfully.", "success")
    except PyMongoError:
        flash("Could not update social links. Check MongoDB connection.", "danger")

    return redirect(url_for("admin"))


@app.route("/admin/live-stream", methods=["POST"])
@login_required
def update_live_stream():
    watch_url = request.form.get("watch_url", "").strip()
    embed_url = get_youtube_embed_url(watch_url)

    if watch_url and not embed_url:
        flash("Please paste a valid YouTube video, live, share, or embed link.", "danger")
        return redirect(url_for("admin"))

    data = {
        "title": request.form.get("title", "").strip() or "Live Streaming",
        "description": request.form.get("description", "").strip() or "Watch the latest live program directly on the website through YouTube Live.",
        "watch_url": watch_url,
        "embed_url": embed_url,
        "updated_at": datetime.now(timezone.utc),
    }

    try:
        db.settings.update_one(
            {"key": "live_stream"},
            {"$set": {"key": "live_stream", "data": data, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        flash("Live stream settings updated successfully.", "success")
    except PyMongoError:
        flash("Could not update live stream settings. Check MongoDB connection.", "danger")

    return redirect(url_for("admin"))


@app.route("/admin/featured-video", methods=["POST"])
@login_required
def update_featured_video():
    videos = []
    for index in range(1, 6):
        watch_url = request.form.get(f"watch_url_{index}", "").strip()
        embed_url = get_youtube_embed_url(watch_url)

        if watch_url and not embed_url:
            flash(f"Please paste a valid YouTube link in Video {index}.", "danger")
            return redirect(url_for("admin"))

        videos.append({
            "watch_url": watch_url,
            "embed_url": embed_url,
        })

    data = {
        "title": request.form.get("title", "").strip() or "Featured Video",
        "description": request.form.get("description", "").strip() or "Watch an important YouTube video directly on the website.",
        "videos": videos,
        "updated_at": datetime.now(timezone.utc),
    }

    try:
        db.settings.update_one(
            {"key": "featured_video"},
            {"$set": {"key": "featured_video", "data": data, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        flash("Featured video updated successfully.", "success")
    except PyMongoError:
        flash("Could not update featured video. Check MongoDB connection.", "danger")

    return redirect(url_for("admin"))


@app.route("/admin/featured-video/<int:index>/delete", methods=["POST"])
@login_required
def delete_featured_video(index):
    if index < 1 or index > 5:
        flash("Unknown video slot.", "danger")
        return redirect(url_for("admin"))

    try:
        current = get_featured_video()
        videos = current.get("videos", [])
        while len(videos) < 5:
            videos.append({"watch_url": "", "embed_url": ""})

        videos[index - 1] = {"watch_url": "", "embed_url": ""}
        db.settings.update_one(
            {"key": "featured_video"},
            {"$set": {"key": "featured_video", "data": {
                "title": current.get("title", "Featured Video"),
                "description": current.get("description", "Watch an important YouTube video directly on the website."),
                "videos": videos,
                "updated_at": datetime.now(timezone.utc),
            }, "updated_at": datetime.now(timezone.utc)}},
            upsert=True,
        )
        flash(f"Video {index} link deleted successfully.", "success")
    except PyMongoError:
        flash("Could not delete featured video link. Check MongoDB connection.", "danger")

    return redirect(url_for("admin"))


@app.route("/admin/members", methods=["POST"])
@login_required
def add_member():
    insert_document(db.members, {
        "name": request.form["name"].strip(),
        "position": request.form["position"].strip(),
        "member_section": normalize_member_section(request.form.get("member_section")),
        "created_at": datetime.now(timezone.utc),
    }, "Member added successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/members/<member_id>/update", methods=["POST"])
@login_required
def update_member(member_id):
    update_document(db.members, member_id, {
        "name": request.form["name"].strip(),
        "position": request.form["position"].strip(),
        "member_section": normalize_member_section(request.form.get("member_section")),
        "updated_at": datetime.now(timezone.utc),
    }, "Member updated successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/members/<member_id>/delete", methods=["POST"])
@login_required
def delete_member(member_id):
    delete_document(db.members, member_id, "Member deleted successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/notifications", methods=["POST"])
@login_required
def add_notification():
    insert_document(db.notifications, {
        "title": request.form["title"].strip(),
        "message": request.form["message"].strip(),
        "created_at": datetime.now(timezone.utc),
    }, "Notification published successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/notifications/<notification_id>/update", methods=["POST"])
@login_required
def update_notification(notification_id):
    update_document(db.notifications, notification_id, {
        "title": request.form["title"].strip(),
        "message": request.form["message"].strip(),
        "updated_at": datetime.now(timezone.utc),
    }, "Notification updated successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/notifications/<notification_id>/delete", methods=["POST"])
@login_required
def delete_notification(notification_id):
    delete_document(db.notifications, notification_id, "Notification deleted successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/programs", methods=["POST"])
@login_required
def add_program():
    insert_document(db.programs, {
        "title": request.form["title"].strip(),
        "description": request.form["description"].strip(),
        "created_at": datetime.now(timezone.utc),
    }, "Academy program added successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/programs/<program_id>/update", methods=["POST"])
@login_required
def update_program(program_id):
    update_document(db.programs, program_id, {
        "title": request.form["title"].strip(),
        "description": request.form["description"].strip(),
        "updated_at": datetime.now(timezone.utc),
    }, "Academy program updated successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/programs/<program_id>/delete", methods=["POST"])
@login_required
def delete_program(program_id):
    delete_document(db.programs, program_id, "Academy program deleted successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/projects", methods=["POST"])
@login_required
def add_project():
    file = request.files.get("file")
    if not file or not file.filename:
        flash("Please choose an image or video for the project.", "warning")
        return redirect(url_for("admin"))

    media_type = get_media_type(file.filename)
    if not media_type:
        flash("Only JPG, PNG, GIF, WEBP, MP4, MOV, and WEBM files are allowed.", "danger")
        return redirect(url_for("admin"))

    upload_result = save_uploaded_file(file, media_type)
    insert_document(db.projects, {
        "title": request.form["title"].strip(),
        "project_date": request.form["project_date"].strip(),
        "description": request.form["description"].strip(),
        "filename": upload_result["filename"],
        "url": upload_result["url"],
        "public_id": upload_result["public_id"],
        "storage": upload_result["storage"],
        "resource_type": upload_result["resource_type"],
        "media_type": media_type,
        "created_at": datetime.now(timezone.utc),
    }, "Project added successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/projects/<project_id>/delete", methods=["POST"])
@login_required
def delete_project(project_id):
    try:
        project = db.projects.find_one({"_id": ObjectId(project_id)}) or {}
    except (PyMongoError, InvalidId):
        project = {}

    delete_saved_media(project)
    delete_document(db.projects, project_id, "Project deleted successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/gallery/<media_id>/update", methods=["POST"])
@login_required
def update_media(media_id):
    update_document(db.gallery, media_id, {
        "title": request.form.get("title", "").strip(),
        "location": request.form.get("location", "").strip(),
        "category": request.form.get("category", "").strip(),
        "updated_at": datetime.now(timezone.utc),
    }, "Media details updated successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/gallery/<media_id>/delete", methods=["POST"])
@login_required
def delete_media(media_id):
    try:
        media = db.gallery.find_one({"_id": ObjectId(media_id)}) or {}
    except (PyMongoError, InvalidId):
        media = {}

    delete_saved_media(media)

    delete_document(db.gallery, media_id, "Media deleted successfully.")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    # app.run(debug=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
