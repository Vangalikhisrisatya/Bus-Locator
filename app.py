import os
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from models import db, Driver, Route, Ground, DailyParking

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access the admin panel.')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key-change-in-prod'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bus_locator.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return Driver.query.get(int(user_id))

@app.route('/')
def index():
    # Student dashboard - view only
    today = date.today()
    routes = Route.query.order_by(Route.name).all()
    
    # Get today's parking records
    daily_records = DailyParking.query.filter_by(date=today).all()
    record_map = {record.route_id: record for record in daily_records}
    
    route_status = []
    for route in routes:
        record = record_map.get(route.id)
        is_today = True
        
        # Fallback to last known update if not updated today
        if not record:
            record = DailyParking.query.filter_by(route_id=route.id).order_by(DailyParking.date.desc(), DailyParking.updated_at.desc()).first()
            is_today = False
            
        if record:
            route_status.append({
                'route_name': route.name,
                'ground_name': record.ground.name,
                'updated_at': record.updated_at.strftime('%I:%M %p'),
                'update_date': record.date.strftime('%b %d, %Y'),
                'is_today': is_today,
                'has_data': True
            })
        else:
            route_status.append({
                'route_name': route.name,
                'ground_name': 'Awaiting Update',
                'updated_at': None,
                'update_date': None,
                'is_today': False,
                'has_data': False
            })
    
    return render_template('student_dashboard.html', route_status=route_status, today=today.strftime('%b %d, %Y'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('driver_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        driver = Driver.query.filter_by(email=email).first()
        if driver and check_password_hash(driver.password_hash, password):
            login_user(driver)
            if driver.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('driver_dashboard'))
        else:
            flash('Invalid email or password.')
            
    return render_template('driver_login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/driver', methods=['GET', 'POST'])
@login_required
def driver_dashboard():
    routes = Route.query.order_by(Route.name).all()
    grounds = Ground.query.order_by(Ground.id).all()
    today = date.today()
    
    if request.method == 'POST':
        route_id = request.form.get('route_id')
        ground_id = request.form.get('ground_id')
        
        if not route_id or not ground_id:
            flash('Please select a route and a ground.')
            return redirect(url_for('driver_dashboard'))
            
        # Check if a record already exists for today and this route
        existing_record = DailyParking.query.filter_by(date=today, route_id=route_id).first()
        if existing_record:
            existing_record.ground_id = ground_id
            existing_record.driver_id = current_user.id
        else:
            new_record = DailyParking(
                date=today,
                route_id=route_id,
                ground_id=ground_id,
                driver_id=current_user.id
            )
            db.session.add(new_record)
        
        db.session.commit()
        flash('Parking location updated successfully!')
        return redirect(url_for('driver_dashboard'))
        
    # Get driver's recent updates for today
    recent_updates = DailyParking.query.filter_by(date=today, driver_id=current_user.id).all()
    
    return render_template('driver_dashboard.html', routes=routes, grounds=grounds, recent_updates=recent_updates)

# --- Admin Routes ---

@app.route('/admin')
@admin_required
def admin_dashboard():
    total_drivers = Driver.query.count()
    total_routes = Route.query.count()
    total_grounds = Ground.query.count()
    
    today = date.today()
    today_updates_count = DailyParking.query.filter_by(date=today).count()
    
    return render_template(
        'admin_dashboard.html',
        total_drivers=total_drivers,
        total_routes=total_routes,
        total_grounds=total_grounds,
        today_updates_count=today_updates_count
    )

@app.route('/admin/drivers', methods=['GET', 'POST'])
@admin_required
def admin_drivers():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = True if request.form.get('is_admin') else False
        
        if not email or not password:
            flash('All fields are required.')
            return redirect(url_for('admin_drivers'))
            
        existing = Driver.query.filter_by(email=email).first()
        if existing:
            flash('Driver/User with this email already exists.')
            return redirect(url_for('admin_drivers'))
            
        new_driver = Driver(
            email=email,
            password_hash=generate_password_hash(password),
            is_admin=is_admin
        )
        db.session.add(new_driver)
        db.session.commit()
        flash('Driver/User added successfully!')
        return redirect(url_for('admin_drivers'))
        
    drivers = Driver.query.order_by(Driver.email).all()
    return render_template('admin_drivers.html', drivers=drivers)

@app.route('/admin/drivers/delete/<int:driver_id>', methods=['POST'])
@admin_required
def delete_driver(driver_id):
    if driver_id == current_user.id:
        flash('You cannot delete your own logged-in admin account!')
        return redirect(url_for('admin_drivers'))
        
    driver = Driver.query.get_or_404(driver_id)
    
    # Delete their parking records
    DailyParking.query.filter_by(driver_id=driver_id).delete()
    
    db.session.delete(driver)
    db.session.commit()
    flash(f'Driver {driver.email} deleted successfully!')
    return redirect(url_for('admin_drivers'))

@app.route('/admin/routes', methods=['GET', 'POST'])
@admin_required
def admin_routes():
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('Route name is required.')
            return redirect(url_for('admin_routes'))
            
        existing = Route.query.filter_by(name=name).first()
        if existing:
            flash('Route already exists.')
            return redirect(url_for('admin_routes'))
            
        new_route = Route(name=name)
        db.session.add(new_route)
        db.session.commit()
        flash('Route added successfully!')
        return redirect(url_for('admin_routes'))
        
    routes = Route.query.order_by(Route.name).all()
    return render_template('admin_routes.html', routes=routes)

@app.route('/admin/routes/delete/<int:route_id>', methods=['POST'])
@admin_required
def delete_route(route_id):
    route = Route.query.get_or_404(route_id)
    
    # Clean up daily parking records for this route
    DailyParking.query.filter_by(route_id=route_id).delete()
    
    db.session.delete(route)
    db.session.commit()
    flash(f'Route "{route.name}" deleted successfully!')
    return redirect(url_for('admin_routes'))

@app.route('/admin/grounds', methods=['GET', 'POST'])
@admin_required
def admin_grounds():
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('Ground name is required.')
            return redirect(url_for('admin_grounds'))
            
        existing = Ground.query.filter_by(name=name).first()
        if existing:
            flash('Ground already exists.')
            return redirect(url_for('admin_grounds'))
            
        new_ground = Ground(name=name)
        db.session.add(new_ground)
        db.session.commit()
        flash('Ground added successfully!')
        return redirect(url_for('admin_grounds'))
        
    grounds = Ground.query.order_by(Ground.name).all()
    return render_template('admin_grounds.html', grounds=grounds)

@app.route('/admin/grounds/delete/<int:ground_id>', methods=['POST'])
@admin_required
def delete_ground(ground_id):
    ground = Ground.query.get_or_404(ground_id)
    
    # Clean up daily parking records for this ground
    DailyParking.query.filter_by(ground_id=ground_id).delete()
    
    db.session.delete(ground)
    db.session.commit()
    flash(f'Ground "{ground.name}" deleted successfully!')
    return redirect(url_for('admin_grounds'))

@app.route('/admin/history')
@admin_required
def admin_history():
    history = DailyParking.query.order_by(DailyParking.date.desc(), DailyParking.updated_at.desc()).all()
    return render_template('admin_history.html', history=history)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
