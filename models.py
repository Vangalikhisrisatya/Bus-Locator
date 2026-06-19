from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class Driver(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    # e.g., "Kakinada via Samalkot"

class Ground(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    # e.g., "Ground 1 (Kakinada Ground)"

class DailyParking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=False)
    ground_id = db.Column(db.Integer, db.ForeignKey('ground.id'), nullable=False)
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    route = db.relationship('Route', backref=db.backref('parkings', lazy=True))
    ground = db.relationship('Ground', backref=db.backref('parkings', lazy=True))
    driver = db.relationship('Driver', backref=db.backref('parkings', lazy=True))
