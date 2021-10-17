from dataclasses import asdict

from app.configs.database import db
from app.exceptions.job_exceptions import FieldCreateJobError
from app.exceptions.users_exceptions import UserNotFoundError
from app.models.contractor_model import ContractorModel
from app.models.job_model import JobModel
from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
import sqlalchemy
import psycopg2

@jwt_required()
def create_job():
    
    try :

        current_contractor = get_jwt_identity()
        
        found_contractor = ContractorModel.query.filter_by(email=current_contractor['email']).first()

        if not found_contractor:
            raise UserNotFoundError

        data = request.json

        data['contractor_id'] = found_contractor.id
        
        
        new_job = JobModel(**data)
                
        db.session.add(new_job)
        
        db.session.commit()
        
        new_job.format_expiration_date()
        
        serialized_data = asdict(new_job)
        
        del serialized_data['contractor']
        
        del serialized_data['developer']
        
        return jsonify(serialized_data), 200
    
    except UserNotFoundError as e:
        return {'message': str(e)}, 404
    
    except sqlalchemy.exc.IntegrityError as e:
        
        if type(e.orig) == psycopg2.errors.NotNullViolation:
            return {'Message': 'Job must be created with name, description, price, difficulty_level and expiration_date'}, 406
    
    except (TypeError, KeyError):
        e = FieldCreateJobError()
        return jsonify(e.message), 406
    
def get_job_by_id(job_id: int):
    job = JobModel.query.filter_by(id=job_id).first()
    if job is None:
        return {"message": "Job does not exist"}, 404
    return jsonify(job)

@jwt_required()
def update_job_by_id(job_id: int):
    ...

@jwt_required()
def delete_job_by_id(job_id: int):
    
    session = current_app.db.session
    current_user = get_jwt_identity()
    
    found_contractor = ContractorModel.query.filter_by(email=current_user['email']).first()
    
    try:
        job = JobModel.query.get(job_id)
        
        if job.contractor_id == found_contractor.id:
            session.delete(job)
            session.commit()
            return '', 204
        
        else:
            return {'message': "You don't have permission to delete this job"}, 403
        
    except AttributeError:
        return {'message': 'job not found'}, 404

def get_all_jobs():
    session = current_app.db.session
    jobs = session.query(JobModel)\
                  .all()
    return jsonify(jobs)
