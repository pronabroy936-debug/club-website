from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
import os

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, flash, redirect, render_template, request, session, url_for
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


def default_programs():
    return [
        {"title": "Cricket", "description": "Batting, bowling, fielding, and match awareness sessions."},
        {"title": "Football", "description": "Ball control, stamina, passing drills, and team play."},
        {"title": "Yoga", "description": "Flexibility, balance, breathing, and recovery routines."},
        {"title": "Karate", "description": "Self-control, strength, confidence, and focused movement."},
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
    ]


def utsav_events():
    return [
        "Swami Vivekananda birthday celebration",
        "Seven-day community festival",
        "Cultural performances and youth programs",
        "Sports events and prize distribution",
        "Social awareness and service activities",
    ]


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


# ---------------- HOME ----------------
@app.route("/")
def home():
    notifications = find_documents(db.notifications, fallback=[])
    return render_template(
        "home.html",
        notifications=notifications[:3],
        profile=organization_profile(),
        activities=community_activities()[:3],
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
    return render_template("members.html", members=data, section=get_section("members"))

# ---------------- ACADEMY ----------------
@app.route("/academy")
def academy():
    programs = find_documents(db.programs)
    if not programs:
        programs = default_programs()
    return render_template("academy.html", programs=programs, section=get_section("academy"))

# ---------------- CONTACT ----------------
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
    media = find_documents(db.gallery)
    programs = find_documents(db.programs)
    sections = get_all_sections()
    return render_template(
        "admin.html",
        members=members,
        notifications=notifications,
        media=media,
        programs=programs,
        sections=sections,
        social_links=get_social_links(),
    )


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

    try:
        db.sections.update_one({"slug": slug}, {"$set": document}, upsert=True)
        flash(f"{document['label']} section updated successfully.", "success")
    except PyMongoError:
        flash("Could not save section content. Check MongoDB connection.", "danger")

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


@app.route("/admin/members", methods=["POST"])
@login_required
def add_member():
    insert_document(db.members, {
        "name": request.form["name"].strip(),
        "position": request.form["position"].strip(),
        "created_at": datetime.now(timezone.utc),
    }, "Member added successfully.")
    return redirect(url_for("admin"))


@app.route("/admin/members/<member_id>/update", methods=["POST"])
@login_required
def update_member(member_id):
    update_document(db.members, member_id, {
        "name": request.form["name"].strip(),
        "position": request.form["position"].strip(),
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

    if media.get("storage") == "cloudinary" and media.get("public_id"):
        cloudinary.uploader.destroy(media["public_id"], resource_type=media.get("resource_type", "image"))
    elif media.get("filename"):
        media_path = Path(app.config["UPLOAD_FOLDER"]) / secure_filename(media["filename"])
        if media_path.exists():
            media_path.unlink()

    delete_document(db.gallery, media_id, "Media deleted successfully.")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    # app.run(debug=True)
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
