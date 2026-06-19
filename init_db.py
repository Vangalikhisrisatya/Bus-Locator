from app import app, db
from models import Driver, Route, Ground
from werkzeug.security import generate_password_hash

def init_db():
    with app.app_context():
        # Drop all tables first to ensure schema updates are applied
        db.drop_all()
        # Create all tables
        db.create_all()

        # Seed Grounds
        if not Ground.query.first():
            grounds = [
                Ground(name="Ground 1 (Kakinada Ground)"),
                Ground(name="Ground 2 (Rajahmundry Ground)"),
                Ground(name="Ground 3 (Pitapuram Ground)")
            ]
            db.session.add_all(grounds)
            
        # Seed Routes
        if not Route.query.first():
            routes = [
                Route(name="Kakinada via Samalkot"),
                Route(name="Kakinada via Peddapuram"),
                Route(name="Rajahmundry via Kovvur"),
                Route(name="Pitapuram via Gollaprolu"),
                Route(name="Tuni Main Route")
            ]
            db.session.add_all(routes)

        # Seed Trusted Driver
        if not Driver.query.filter_by(email="driver@college.edu").first():
            test_driver = Driver(
                email="driver@college.edu",
                password_hash=generate_password_hash("driver123"),
                is_admin=False
            )
            db.session.add(test_driver)

        # Seed Trusted Admin
        if not Driver.query.filter_by(email="admin@college.edu").first():
            test_admin = Driver(
                email="admin@college.edu",
                password_hash=generate_password_hash("admin123"),
                is_admin=True
            )
            db.session.add(test_admin)

        db.session.commit()
        print("Database initialized and seeded successfully!")

if __name__ == '__main__':
    init_db()
