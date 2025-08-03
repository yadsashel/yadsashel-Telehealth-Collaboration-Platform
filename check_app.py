from models import ScheduleAppointment, User, engine
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)
session = Session()

def check_appointments():
    print("Checking appointments for missing or invalid patients...\n")

    appointments = session.query(ScheduleAppointment).all()
    problems_found = False

    for appt in appointments:
        if not appt.patient_id:
            print(f"Appointment ID {appt.id} has NO patient_id linked (None or 0).")
            problems_found = True
        else:
            # Check if patient_id exists in users table
            user = session.query(User).filter_by(id=appt.patient_id).first()
            if not user:
                print(f"Appointment ID {appt.id} linked to NON-EXISTENT patient_id {appt.patient_id}.")
                problems_found = True

    if not problems_found:
        print("✅ All appointments have valid patient links!")

if __name__ == "__main__":
    check_appointments()
    session.close()
