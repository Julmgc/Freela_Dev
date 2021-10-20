from flask import Blueprint
from app.controllers.contractor_controller import create_profile, get_all_contractor_jobs, update_profile_info, delete_profile, get_all_contractors, get_profile_info, get_contractor_jobs_by_progress_status

bp = Blueprint('bp_contractor', __name__, url_prefix='/contractors')

bp.post('/signup')(create_profile)

bp.get('/profile')(get_profile_info)
bp.get('')(get_all_contractors)
bp.get('/jobs')(get_contractor_jobs_by_progress_status)
bp.get('/jobs')(get_all_contractor_jobs)

bp.patch('/update')(update_profile_info)

bp.delete('/delete')(delete_profile)






