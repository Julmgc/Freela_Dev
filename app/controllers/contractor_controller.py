from dataclasses import asdict

import psycopg2
import sqlalchemy
from app.configs.database import db
from app.exceptions.contractor_exceptions import FieldCreateContractorError
from app.exceptions.field_upgrade_exeptions import FieldUpdateContractorError
from app.exceptions.invalid_email_exceptions import InvalidEmailError
from app.exceptions.invalid_password_exceptions import InvalidPasswordError
from app.exceptions.users_exceptions import UserNotFoundError
from app.models.contractor_model import ContractorModel
from app.models.developer_model import DeveloperModel
from app.models.job_model import JobModel
from flask import current_app, jsonify, request
from flask_jwt_extended import (get_jwt_identity,
                                jwt_required)
from sqlalchemy import exc
from datetime import datetime

def create_profile():
    
    try:
        data = request.json
        if not ContractorModel.verify_pattern_password(data['password']):
            return "Password must contain from 6 to maximum 20 characters, at least one number, upper and lower case and one special character", 409
        if not ContractorModel.verify_pattern_email(data['email']):
            return "Email must contain @ and .", 409
        if ContractorModel.unique_email(data['email']):
            return "You've already registered with this email as a contractor.", 409
        if "cnpj" in data:
            if ContractorModel.unique_cnpj(data['cnpj']):
                return "You've already registered with this CNPJ as a contractor.", 409
            if not ContractorModel.verify_cnpj(data['cnpj']):
                return "cnpj must be in this format: 00.000.000/0000-00.", 409
                
        email_already_used_as_developer = DeveloperModel.query.filter_by(email=data['email']).first()
        if email_already_used_as_developer:
            return {'message': 'Email is already used as developer, please use another one for your contractor account.'}, 409

        session = current_app.db.session
        password_to_hash = data.pop("password")
        new_user = ContractorModel(**data)
        new_user.password = password_to_hash
        session.add(new_user)
        session.commit()
        found_user = ContractorModel.query.filter_by(email=data["email"]).first()
        return jsonify(found_user), 200
    
    except sqlalchemy.exc.IntegrityError as e :
        if type(e.orig) == psycopg2.errors.NotNullViolation:
            return {'Message': 'contractor must be created with name, email and password, CNPJ is optional.'}, 400
        
    except exc.IntegrityError as e:
        if type(e.orig) == psycopg2.errors.UniqueViolation:  
            return {"message": "User already exists"}, 409

    except (KeyError, TypeError):
        err = FieldCreateContractorError()
        return jsonify(err.message), 406

@jwt_required()
def get_profile_info():
    profile_info = get_jwt_identity()
    
    return jsonify(profile_info), 200

@jwt_required()
def update_profile_info():
        
    try:
        data = request.json
        
        current_user = get_jwt_identity()
        
        user = ContractorModel.query.filter(ContractorModel.email == current_user['email']).first()
        
        if 'email' in data.keys():
            found_email = DeveloperModel.query.filter(DeveloperModel.email == data['email']).first()
            
            if found_email:
                return {"Message":"this email is already being used"}, 409
            
            else:
                if not ContractorModel.verify_pattern_email(data['email']):
                    raise InvalidEmailError(data)
                
        if 'password' in data.keys():
            
            if not ContractorModel.verify_pattern_password(data['password']):
                raise InvalidPasswordError(data)
            
            contractor = ContractorModel(password=data.pop('password'))
            
            data['password_hash'] = contractor.password_hash
        
        if 'cnpj' in data.keys():
            if not ContractorModel.verify_cnpj(data['cnpj']):
                return {'Message': "cnpj must be in this format: 00.000.000/0000-00."}, 406
            
        ContractorModel.query.filter_by(id=user.id).update(data)
            
        db.session.commit()
    
        updated_data = ContractorModel.query.get(user.id)
        
        return jsonify(updated_data), 200
    
    except sqlalchemy.exc.IntegrityError as e :
        
        if type(e.orig) == psycopg2.errors.NotNullViolation:
            return {'Message': 'Contractor must be updated with name, email, password or cnpj'}, 400
        
        if type(e.orig) ==  psycopg2.errors.UniqueViolation:
            return {'Message': str(e.orig).split('\n')[0]}, 409
        
    except sqlalchemy.exc.InvalidRequestError:
        
        if data.get('password_hash'):
            
            del data['password_hash']
        
        err = FieldUpdateContractorError()
        
        return jsonify(err.message), 409
    
    except sqlalchemy.exc.ProgrammingError:
         return {'Message': "fields are empty"}, 400

    except InvalidEmailError:
        return {'Message': "You sent an invalid email. Use this model: test@gmail.com"}, 406

    except InvalidPasswordError:
        return {'Message': "Password must contain from 6 to maximum 20 characters, at least one number, upper and lower case and one special character"}, 406
    
@jwt_required()
def delete_profile():
    contractor = get_jwt_identity()
    found_contractor = ContractorModel.query.filter_by(email=contractor["email"]).first()
    if found_contractor is None:
        return {"message": "Contractor not found!"}, 404
    if contractor['email'] == found_contractor.email:
        current_app.db.session.delete(found_contractor)
        current_app.db.session.commit()
    return "", 204

    
def get_all_contractors():
    session = current_app.db.session
    contractors = session.query(ContractorModel)\
                  .all()
    return jsonify(contractors)


@jwt_required()
def get_all_contractor_jobs():
    current_contractor = get_jwt_identity()
    found_contractor = ContractorModel.query.filter_by(email=current_contractor['email']).first()
    if found_contractor == None:
        return {"message": "Contractor account not found"}, 404
    data = request.args
    page = request.args.get('page', 1, int)
    per_page = request.args.get('per_page', 5, int)
    jobs = []


    if 'progress' not in data:
        query = JobModel.query.filter(JobModel.contractor_id == found_contractor.id).paginate(page=page, per_page=per_page, error_out=True).items
        formatted_job_list = [asdict(item) for item in query]
        for d in formatted_job_list:
            if d['developer']:
                d['developer']['birthdate'] = datetime.strftime(d['developer']['birthdate'], "%d/%m/%y")
            d['expiration_date'] = datetime.strftime(d['expiration_date'], "%d/%m/%y %H:%M")
            del d['contractor']
            jobs.append(d)
        return jsonify(jobs)
    elif 'progress' in data:
        if data['progress'] == 'None':
            query = JobModel.query.filter(JobModel.contractor_id == found_contractor.id, JobModel.progress == None).paginate(page=page, per_page=per_page, error_out=True).items
        else:
            query = JobModel.query.filter(JobModel.contractor_id == found_contractor.id, JobModel.progress == data['progress']).paginate(page=page, per_page=per_page, error_out=True).items
        if query:
            formatted_job_list = [asdict(item) for item in query]
            
            for d in formatted_job_list:
                if d['developer']:
                    d['developer']['birthdate'] = datetime.strftime(d['developer']['birthdate'], "%d/%m/%y")
                d['expiration_date'] = datetime.strftime(d['expiration_date'], "%d/%m/%y %H:%M")
                del d['contractor']
                jobs.append(d)
            
        return jsonify(jobs)
    else:
        return {"message": "The values for job progress are:  None, ongoing and completed"}, 406





        

