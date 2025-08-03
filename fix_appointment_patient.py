from sqlalchemy.orm import sessionmaker
from models import engine, ScheduleAppointment

Session = sessionmaker(bind=engine)
session = Session()

appointment_id_to_fix = 1
patient_id_to_set = 1  # set to a valid user id from your users table

appointment = session.query(ScheduleAppointment).get(appointment_id_to_fix)
if appointment:
    appointment.patient_id = patient_id_to_set
    session.commit()
    print(f"✅ Appointment {appointment_id_to_fix} updated with patient_id={patient_id_to_set}")
else:
    print(f"❌ Appointment {appointment_id_to_fix} not found")

session.close()
