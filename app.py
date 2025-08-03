import os
import uuid
import requests
from datetime import date as dt_date
from datetime import datetime, timedelta
from flask_cors import CORS
from flask import Flask, render_template, redirect, request, flash, url_for, session, jsonify
import json
import re
import tempfile
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, Text, DateTime ,ForeignKey
from sqlalchemy.orm import sessionmaker
from models import User, SQLASession, engine, ScheduleAppointment, Message
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from flask_socketio import SocketIO, emit, join_room


app = Flask(__name__)
CORS(app)

# App config
SQLASession = sessionmaker(bind=engine)
load_dotenv()

socketio = SocketIO(app)

app.secret_key = os.getenv('SECRET_KEY')
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
TOGETHER_MODEL = "mistralai/Mistral-7B-Instruct-v0.1"


# Setup upload folder
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'profile_pics')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

today = dt_date.today()

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

def create_google_meet_event(summary, description, start_datetime, end_datetime, email):
    # Load the JSON string from the .env and convert to dict
    creds_json = os.getenv('GOOGLE_CREDS_JSON')
    creds_dict = json.loads(creds_json)

    # Save the JSON to a temporary file
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as tmp:
        json.dump(creds_dict, tmp)
        tmp.flush()

        # Use the temp file to initialize the flow
        flow = InstalledAppFlow.from_client_secrets_file(tmp.name, SCOPES)
        creds = flow.run_local_server(port=5002)

    service = build('calendar', 'v3', credentials=creds)

    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_datetime.isoformat(),
            'timeZone': 'Africa/Casablanca',
        },
        'end': {
            'dateTime': end_datetime.isoformat(),
            'timeZone': 'Africa/Casablanca',
        },
        'attendees': [{'email': email}],
        'conferenceData': {
            'createRequest': {
                'requestId': f"meet-{int(datetime.datetime.now().timestamp())}"
            }
        },
    }

    event = service.events().insert(calendarId='primary', body=event, conferenceDataVersion=1).execute()
    return event.get('hangoutLink')

# make the user to be existin all the pages
@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    if user_id:
        with SQLASession() as db_session:
            user = db_session.query(User).filter_by(id=user_id).first()
            return dict(user=user)
    return dict(user=None)

@socketio.on('join_room')
def handle_join(data):
    join_room(str(data['user_id']))  # Join personal room

@socketio.on('send_message')
def handle_send_message(data):
    with SQLASession() as db_session:
        msg = Message(
            sender_id=data['sender_id'],
            receiver_id=data['receiver_id'],
            content=data['content']
        )
        db_session.add(msg)
        db_session.commit()

        emit('receive_message', {
            'sender_id': msg.sender_id,
            'receiver_id': msg.receiver_id,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        }, room=str(msg.receiver_id))

        emit('receive_message', {
            'sender_id': msg.sender_id,
            'receiver_id': msg.receiver_id,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        }, room=str(msg.sender_id))  # sender also gets message

@socketio.on('typing')
def handle_typing(data):
    emit('typing', {
        'sender_id': data['sender_id'],
    }, room=str(data['receiver_id']))



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('Services.html')

@app.route('/contact')
def contact():
    return render_template('Contact.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/faq')
def faq():
    return render_template('faq.html')

# ==== register page ====
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            user_type = request.form.get('user_type')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            password = request.form.get('password')
            sc_code = request.form.get('sc_code')
            tel = request.form.get('tel')
            confirm_password = request.form.get('confirm_password')

            if password != confirm_password:
                flash('Passwords do not match!', 'error')
                return redirect(url_for('register'))

            hashed_password = generate_password_hash(password)

            with SQLASession() as db_session:
                existing_user = db_session.query(User).filter_by(email=email).first()
                if existing_user:
                    flash('Email is already registered.', 'error')
                    return redirect(url_for('register'))

                new_user = User(
                    user_type=user_type,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    tel=tel,
                    password=hashed_password,
                    sc_code=sc_code,
                    image_url='',
                )
                db_session.add(new_user)
                db_session.commit()

                flash('Successfully registered!', 'success')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f'Unexpected error: {str(e)}', 'error')
            return redirect(url_for('register'))

    return render_template('register.html')

# ==== login route ====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_type = request.form.get('user_type').strip()
        first_name = request.form.get('first_name').strip()
        password = request.form.get('password')
        sc_code = request.form.get('sc_code').strip()

        with SQLASession() as db_session:
            user = db_session.query(User).filter(
                User.user_type == user_type,
                func.lower(User.first_name) == first_name.lower(),
                User.sc_code == sc_code
            ).first()

        if not user or not check_password_hash(user.password, password):
            flash('Invalid credentials! Please try again', 'error')
            return redirect(url_for('login'))

        session['user_id'] = user.id
        session['user_type'] = user.user_type
        session['first_name'] = user.first_name
        session['sc_code'] = user.sc_code

        if user.user_type == 'patient':
            return redirect(url_for('patient_dash'))
        elif user.user_type == 'doctor':
            return redirect(url_for('doctor_dash'))
        elif user.user_type == 'nurse':
            return redirect(url_for('nurse_dash'))

        flash('Unexpected error: invalid user type!', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')

# ==== logout route ====
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# ==== AI chating ====
@app.route('/api/ask', methods=['POST'])
def ask():
    data = request.get_json()
    user_prompt = data.get("prompt", "").strip()
    full_prompt = (
        "You are a helpful, kind, and professional medical assistant. "
        "Answer clearly and politely using friendly and natural language. Only use lists if there are distinct steps or multiple recommendations. For simple answers, just explain in a few clear sentences.\n\n"
        f"Question: {user_prompt}\n\nAnswer:"
    )

    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    json_data = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "prompt": full_prompt,
        "max_tokens": 300,
        "temperature": 0.7
    }

    response = requests.post("https://api.together.xyz/v1/completions", headers=headers, json=json_data)
    if response.ok:
        reply = response.json()["choices"][0]["text"].strip()
        if not reply or "I don't understand" in reply or "I'm not sure" in reply:
            reply = "Sorry, I couldn’t understand your question clearly. Could you rephrase it?"
        return jsonify({"response": reply})
    return jsonify({"error": "Failed to get AI response"}), 500

# ====== diagnosis page ======

@app.route('/diagnosis_page')
def diagnosis_page():
    return render_template('diagnosis.html')


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    messages = data.get("messages", [])

    system_prompt = {
        "role": "system",
        "content": (
            "You're a helpful medical AI assistant. You help the patient understand symptoms, answer health-related questions, "
            "and when they ask to show a body part, you return a JSON like: "
            "{\"action\": \"highlight\", \"target\": \"heart\", \"message\": \"Here is the heart.\"} "
            "If they describe symptoms, reply normally AND include final diagnosis in JSON like: "
            "{\"diagnosis\": \"...\", \"target\": \"...\"} at the end of your response."
        )
    }

    messages.insert(0, system_prompt)

    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }

    body = {
        "model": TOGETHER_MODEL,
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 500
    }

    try:
        res = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=body)
        result = res.json()
        reply = result["choices"][0]["message"]["content"]

        # Extract both diagnosis or action commands
        diagnosis = None
        target = None
        message = None
        action = None

        match = re.search(r'\{.*?\}', reply, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            diagnosis = parsed.get("diagnosis")
            target = parsed.get("target")
            action = parsed.get("action")
            message = parsed.get("message")

        return jsonify({
            "reply": reply,
            "diagnosis": diagnosis,
            "target": target,
            "action": action,
            "message": message
        })

    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})




@app.route('/patient_dash')
def patient_dash():
    return render_template('patient_dash.html')

# ==== patient appointment ====
@app.route('/patient_appoin')
def patient_appoin():
    with SQLASession() as db_session:
        all_appointments = db_session.query(ScheduleAppointment).order_by(ScheduleAppointment.date.desc()).all()

        today = dt_date.today()

        print("TODAY:", today)
        print("All appointments:")
        for a in all_appointments:
            print(f"ID: {a.id}, Date: {a.date}, Type: {a.appointment_type}")
        
        upcoming_appointments = [a for a in all_appointments if a.date >= today]
        past_appointments = [a for a in all_appointments if a.date < today]

        print("Upcoming appointments:")
        for a in upcoming_appointments:
            print(f"ID: {a.id}, Date: {a.date}")
        
        print("Past appointments:")
        for a in past_appointments:
            print(f"ID: {a.id}, Date: {a.date}")

        return render_template('patient_appoin.html', upcoming_appointments=upcoming_appointments, past_appointments=past_appointments)


# ==== schedule an appointment ====
@app.route('/schedule_app', methods=['GET', 'POST'])
def schedule_app():
    if request.method == 'POST':
        try:
            appointment_type = request.form.get('appointmentType')
            date_str = request.form.get('date')
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            time = request.form.get('time')
            reason = request.form.get('reason')

            with SQLASession() as db_session:
                schedule_appointments = ScheduleAppointment(
                    appointment_type=appointment_type,
                    date=date,
                    time=time,
                    reason=reason
                    )
                db_session.add(schedule_appointments)
                db_session.commit()

            flash('appointement schedulded sucessfull', 'sucess')
            return redirect(url_for('patient_appoin'))

        except Exception as e:
            flash(f'Unexpected error: {str(e)}', 'error')
            return redirect(url_for('patient_dash'))

    return render_template('patient_dash.html')

@app.route('/cancel_appointment/<int:appointment_id>', methods=['DELETE'])
def cancel_appointment(appointment_id):
    try:
        with SQLASession() as db_session:
            appointment = db_session.query(ScheduleAppointment).get(appointment_id)
            if appointment:
                db_session.delete(appointment)
                db_session.commit()
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'message': 'Appointment not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    
#join the metting
@app.route('/join_meeting/<int:appointment_id>', methods=['POST'])
def join_meeting(appointment_id):
    with SQLASession() as db_session:
        appointment = db_session.query(ScheduleAppointment).get(appointment_id)

        if not appointment:
            flash("❌ Appointment not found.", "error")
            return redirect(url_for('patient_appoin'))

        if not appointment.patient_id:
            flash("❌ This appointment is not linked to any patient.", "error")
            return redirect(url_for('patient_appoin'))

        user = db_session.query(User).get(appointment.patient_id)
        if not user:
            flash("❌ Patient not found.", "error")
            return redirect(url_for('patient_appoin'))

        try:
            meet_link = create_google_meet_event(
                summary=f"Appointment: {appointment.appointment_type}",
                description=appointment.reason,
                start_datetime=datetime.combine(appointment.date, appointment.time),
                end_datetime=datetime.combine(appointment.date, appointment.time) + timedelta(minutes=30),
                email=user.email
            )
        except Exception as e:
            flash(f'Failed to create meeting: {str(e)}', 'error')
            return redirect(url_for('patient_appoin'))

        return redirect(meet_link)


@app.route('/patient_mess', defaults={'contact_id': None}, methods=['GET', 'POST'])
@app.route('/patient_mess/<int:contact_id>', methods=['GET', 'POST'])
def patient_mess(contact_id):
    current_user_id = session.get('user_id')

    with SQLASession() as db_session:
        # جِب كل الدكاترة والنيرسات باش المريض يقدر يرسل ليهم
        contacts = db_session.query(User).filter(User.user_type.in_(['doctor', 'nurse'])).all()
        messages = []
        contact = None

        if contact_id:
            contact = db_session.query(User).filter_by(id=contact_id).first()

            if contact:
                messages = db_session.query(Message).filter(
                    ((Message.sender_id == current_user_id) & (Message.receiver_id == contact_id)) |
                    ((Message.sender_id == contact_id) & (Message.receiver_id == current_user_id))
                ).order_by(Message.timestamp.asc()).all()

            # إرسال رسالة جديدة
            if request.method == 'POST':
                content = request.form.get('content')
                if content:
                    msg = Message(sender_id=current_user_id, receiver_id=contact_id, content=content)
                    db_session.add(msg)
                    db_session.commit()
                    return redirect(url_for('patient_mess', contact_id=contact_id))

        return render_template("patient_mess.html",
                               contacts=contacts,
                               contact=contact,
                               messages=messages,
                               contact_id=contact_id,
                               current_user_id=current_user_id)


# ==== Patient Profile ====
@app.route('/patient_prf', methods=['GET', 'POST'])
def patient_prf():
    user_id = session.get('user_id')
    user_type = session.get('user_type')

    if not user_id or user_type != 'patient':
        flash('Access denied or please log in.', 'error')
        return redirect(url_for('login'))

    with SQLASession() as db_session:
        user = db_session.query(User).filter_by(id=user_id, user_type='patient').first()
        if not user:
            flash('Patient profile not found.', 'error')
            return redirect(url_for('login'))

        if request.method == 'POST':
            # Same update logic here
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            tel = request.form.get('tel')
            sc_code = request.form.get('sc_code')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if password or confirm_password:
                if password != confirm_password:
                    flash('Passwords do not match!', 'error')
                    return redirect(url_for('patient_prf'))
                user.password = generate_password_hash(password)

            if email != user.email:
                existing_user = db_session.query(User).filter_by(email=email).first()
                if existing_user:
                    flash('Email is already registered by another user.', 'error')
                    return redirect(url_for('patient_prf'))
                user.email = email

            user.first_name = first_name
            user.last_name = last_name
            user.tel = tel
            user.sc_code = sc_code

            image = request.files.get('image')
            if image and image.filename != '':
                filename = secure_filename(image.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image.save(upload_path)
                user.image_url = f"uploads/profile_pics/{unique_filename}".replace("\\", "/")

            db_session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('patient_prf'))

        return render_template('patient_prf.html', user=user)

# ====== doctor's dash ======
@app.route('/doctor_dash')
def doctor_dash():

     if 'user_id' not in session or session.get('user_type') != 'doctor':
        flash("⛔ Unauthorized access.", "error")
        return redirect(url_for('login'))
     
     with SQLASession() as db_session:
        all_appointments = db_session.query(ScheduleAppointment).order_by(ScheduleAppointment.date.desc()).all()

        today = dt_date.today()

        print("TODAY:", today)
        print("All appointments:")
        for a in all_appointments:
            print(f"ID: {a.id}, Date: {a.date}, Type: {a.appointment_type}")
        
        upcoming_appointments = [a for a in all_appointments if a.date >= today]
        past_appointments = [a for a in all_appointments if a.date < today]

        print("Upcoming appointments:")
        for a in upcoming_appointments:
            print(f"ID: {a.id}, Date: {a.date}")
        
        print("Past appointments:")
        for a in past_appointments:
            print(f"ID: {a.id}, Date: {a.date}")

        return render_template('doctor_dash.html', upcoming_appointments=upcoming_appointments)


# ======== doctor's messages ======
@app.route('/doc_mess', defaults={'contact_id': None}, methods=['GET', 'POST'])
@app.route('/doc_mess/<int:contact_id>', methods=['GET', 'POST'])
def doc_mess(contact_id):
    current_user_id = session.get('user_id')

    with SQLASession() as db_session:
        # جِب كل الدكاترة والنيرسات باش المريض يقدر يرسل ليهم
        contacts = db_session.query(User).filter(User.user_type.in_(['patient', 'nurse'])).all()
        messages = []
        contact = None

        if contact_id:
            contact = db_session.query(User).filter_by(id=contact_id).first()

            if contact:
                messages = db_session.query(Message).filter(
                    ((Message.sender_id == current_user_id) & (Message.receiver_id == contact_id)) |
                    ((Message.sender_id == contact_id) & (Message.receiver_id == current_user_id))
                ).order_by(Message.timestamp.asc()).all()

            # إرسال رسالة جديدة
            if request.method == 'POST':
                content = request.form.get('content')
                if content:
                    msg = Message(sender_id=current_user_id, receiver_id=contact_id, content=content)
                    db_session.add(msg)
                    db_session.commit()
                    return redirect(url_for('doc_mess', contact_id=contact_id))

        return render_template("doc_mess.html",
                               contacts=contacts,
                               contact=contact,
                               messages=messages,
                               contact_id=contact_id,
                               current_user_id=current_user_id)

# ==== Doctor Profile ====
@app.route('/doc_prf', methods=['GET', 'POST'])
def doc_prf():
    user_id = session.get('user_id')
    user_type = session.get('user_type')

    if not user_id or user_type != 'doctor':
        flash('Access denied or please log in.', 'error')
        return redirect(url_for('login'))

    with SQLASession() as db_session:
        user = db_session.query(User).filter_by(id=user_id, user_type='doctor').first()
        if not user:
            flash('Doctor profile not found.', 'error')
            return redirect(url_for('login'))

        if request.method == 'POST':
            # Same update logic as your profile route
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            tel = request.form.get('tel')
            sc_code = request.form.get('sc_code')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if password or confirm_password:
                if password != confirm_password:
                    flash('Passwords do not match!', 'error')
                    return redirect(url_for('doc_prf'))
                user.password = generate_password_hash(password)

            if email != user.email:
                existing_user = db_session.query(User).filter_by(email=email).first()
                if existing_user:
                    flash('Email is already registered by another user.', 'error')
                    return redirect(url_for('doc_prf'))
                user.email = email

            user.first_name = first_name
            user.last_name = last_name
            user.tel = tel
            user.sc_code = sc_code

            image = request.files.get('image')
            if image and image.filename != '':
                filename = secure_filename(image.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image.save(upload_path)
                user.image_url = f"uploads/profile_pics/{unique_filename}".replace("\\", "/")

            db_session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('doc_prf'))

        return render_template('doc_prf.html', user=user)


@app.route('/doc_appoin', methods=['POST', 'GET'])
def doc_appoin():
     with SQLASession() as db_session:
        all_appointments = db_session.query(ScheduleAppointment).order_by(ScheduleAppointment.date.desc()).all()

        today = dt_date.today()

        print("TODAY:", today)
        print("All appointments:")
        for a in all_appointments:
            print(f"ID: {a.id}, Date: {a.date}, Type: {a.appointment_type}")
        
        upcoming_appointments = [a for a in all_appointments if a.date >= today]

        print("Upcoming appointments:")
        for a in upcoming_appointments:
            print(f"ID: {a.id}, Date: {a.date}")

        return render_template('doc_appoin.html', appointments=upcoming_appointments)

@app.route('/nurse_dash')
def nurse_dash():
    return render_template('nurse_dash.html')

@app.route('/nur_patient')
def nur_patient():
    return render_template('nur_patient.html')

@app.route('/nur_mess', defaults={'contact_id': None}, methods=['GET', 'POST'])
@app.route('/nur_mess/<int:contact_id>', methods=['GET', 'POST'])
def nur_mess(contact_id):
    current_user_id = session.get('user_id')

    with SQLASession() as db_session:
        # جِب كل الدكاترة والنيرسات باش المريض يقدر يرسل ليهم
        contacts = db_session.query(User).filter(User.user_type.in_(['doctor', 'patient'])).all()
        messages = []
        contact = None

        if contact_id:
            contact = db_session.query(User).filter_by(id=contact_id).first()

            if contact:
                messages = db_session.query(Message).filter(
                    ((Message.sender_id == current_user_id) & (Message.receiver_id == contact_id)) |
                    ((Message.sender_id == contact_id) & (Message.receiver_id == current_user_id))
                ).order_by(Message.timestamp.asc()).all()

            # إرسال رسالة جديدة
            if request.method == 'POST':
                content = request.form.get('content')
                if content:
                    msg = Message(sender_id=current_user_id, receiver_id=contact_id, content=content)
                    db_session.add(msg)
                    db_session.commit()
                    return redirect(url_for('nur_mess', contact_id=contact_id))

        return render_template("nur_mess.html",
                               contacts=contacts,
                               contact=contact,
                               messages=messages,
                               contact_id=contact_id,
                               current_user_id=current_user_id)

# ==== Nurse Profile ====
@app.route('/nur_prf', methods=['GET', 'POST'])
def nur_prf():
    user_id = session.get('user_id')
    user_type = session.get('user_type')

    if not user_id or user_type != 'nurse':
        flash('Access denied or please log in.', 'error')
        return redirect(url_for('login'))

    with SQLASession() as db_session:
        user = db_session.query(User).filter_by(id=user_id, user_type='nurse').first()
        if not user:
            flash('Nurse profile not found.', 'error')
            return redirect(url_for('login'))

        if request.method == 'POST':
            # Same update logic here
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')
            tel = request.form.get('tel')
            sc_code = request.form.get('sc_code')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if password or confirm_password:
                if password != confirm_password:
                    flash('Passwords do not match!', 'error')
                    return redirect(url_for('nur_prf'))
                user.password = generate_password_hash(password)

            if email != user.email:
                existing_user = db_session.query(User).filter_by(email=email).first()
                if existing_user:
                    flash('Email is already registered by another user.', 'error')
                    return redirect(url_for('nur_prf'))
                user.email = email

            user.first_name = first_name
            user.last_name = last_name
            user.tel = tel
            user.sc_code = sc_code

            image = request.files.get('image')
            if image and image.filename != '':
                filename = secure_filename(image.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                upload_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image.save(upload_path)
                user.image_url = f"uploads/profile_pics/{unique_filename}".replace("\\", "/")

            db_session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('nur_prf'))

        return render_template('nur_prf.html', user=user)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
