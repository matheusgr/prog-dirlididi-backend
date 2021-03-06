from flask import request
from flask_restful import Resource, marshal_with, fields
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.course import Course
from models.problem import Problem, Solution, PublishRequest
from models.user import User
from services.course_service import CourseService
from services.problem_service import ProblemService
from services.user_service import UserService
from exceptions import MissingAttribute, Unauthorized, BadRequest
from config.callbacks import verify_attributes
from util.auth import get_jwt_user

class ProblemDetail(Resource):

    problem_service = ProblemService()

    @marshal_with(Problem.api_fields)
    def get(self, key):
        return self.problem_service.get_problem_by_key(key)

    @jwt_required
    @marshal_with(Problem.api_fields)
    def put(self, key):
        user_id = get_jwt_identity()
        return self.problem_service.update_problem(user_id, key, request.get_json())
    
    def delete(self, key):
        self.problem_service.delete_problem(key)
        return {}


class ProblemList(Resource):

    user_service = UserService()
    problem_service = ProblemService()

    @marshal_with(Problem.api_fields)
    def get(self):
        name = request.args.get('name')
        return self.problem_service.get_all_public(name)

    @jwt_required
    @verify_attributes(Problem.required_attributes)
    @marshal_with(Problem.api_fields)
    def post(self):
        id = get_jwt_identity()
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        tip = data.get('tip')
        tests = data.get('tests')
        publish = data.get('publish')
        tags = data.get('tags')
        return self.user_service.add_problem(id, name, description, tip, publish, tests, tags)


class UserAuth(Resource):

    user_service = UserService()

    @verify_attributes(['tokenId'])
    def post(self):
        data = request.get_json()
        token = data.get('tokenId')
        return {"jwt": get_jwt_user(token)}

class UserDetail(Resource):

    user_service = UserService()

    @jwt_required
    @marshal_with(User.api_fields)
    def get(self):
        id = get_jwt_identity()
        return self.user_service.get_user_by_id(id)


class SolveProblem(Resource):

    user_service = UserService()

    @verify_attributes(Solution.required_attributes)
    @marshal_with(Solution.api_fields)
    def post(self):
        data = request.get_json()
        user_token = data.get('token')
        problem_key = data.get('key')
        code = data.get('code')
        tests = data.get('tests')
        solution = self.user_service.try_solution(user_token, problem_key, code, tests)
        return solution
    
    @jwt_required
    @marshal_with(Solution.api_fields)
    def get(self):
        return Solution.query.all()


class CourseCRUD(Resource):

    course_service = CourseService()

    @verify_attributes(Course.required_attributes)
    @jwt_required
    @marshal_with(Course.api_fields)
    def post(self):
        user_id = get_jwt_identity()
        data = request.get_json()
        name = data.get('name')
        description = data.get('description')
        language = data.get('language')
        problems = data.get('problems')
        return self.course_service.create_course(user_id, name, description, language, problems)

    @marshal_with(Course.api_fields)
    def get(self):
        return self.course_service.get_all()


class UserCourses(Resource):

    course_service = CourseService()

    @jwt_required
    def get(self):
        user_id = get_jwt_identity()
        return self.course_service.get_all(user_id)


class CourseIdDetail(Resource):

    LEAVE_ACTION = 'leave'
    JOIN_ACTION = 'join'

    user_service = UserService()
    course_service = CourseService()

    @marshal_with(Course.api_fields)
    def get(self, id):
        return self.course_service.get_course_by_id(id)
    
    @verify_attributes(['action'])
    @jwt_required
    @marshal_with(Course.api_fields)
    def post(self, id):
        user_id = get_jwt_identity()
        data = request.get_json()
        action = data.get('action')
        if action == self.JOIN_ACTION:
            return self.course_service.assign_user_to_course(user_id, course_id=id)
        elif action == self.LEAVE_ACTION:
            return self.course_service.remove_user_from_course(user_id, course_id=id)
        else:
            raise BadRequest("'{}' action is not valid".format(action))

    @jwt_required
    @marshal_with(Course.api_fields)
    def put(self, id):
        user_id = get_jwt_identity()
        return self.course_service.update_course(user_id, request.get_json(), id=id)

    @jwt_required
    def delete(self, id):
        user_id = get_jwt_identity()
        self.course_service.delete_course(user_id, id)
        return {}

class CourseTokenDetail(Resource):

    LEAVE_ACTION = 'leave'
    JOIN_ACTION = 'join'

    course_service = CourseService()

    @marshal_with(Course.api_fields)
    def get(self, token):
        return self.course_service.get_course_by_token(token)


class Info(Resource):

    FIELDS = {
        "users": fields.Integer,
        "courses": fields.Integer,
        "problems": fields.Integer,
        "solutions": fields.Integer,
        "topUsers": fields.Nested({
            "id": fields.Integer(attribute="_id"),
            "email": fields.String,
            "name": fields.String,
            "solutions": fields.Integer(attribute="solution_qnt")
        }),
        "topCourses": fields.Nested({
            "id": fields.Integer(attribute="_id"),
            "token": fields.String,
            "members": fields.Integer(attribute="member_qnt"),
            "name": fields.String,
            "language": fields.String,
        })
    }

    user_service = UserService()
    course_service = CourseService()
    problem_service = ProblemService()

    @marshal_with(FIELDS)
    def get(self):
        return {
            "users": len(self.user_service.get_all()),
            "courses": len(self.course_service.get_all()),
            "problems": len(self.problem_service.get_all()),
            "solutions": len([s for user in self.user_service.get_all() for s in user.solutions]),
            "topUsers": self.user_service.get_top_users(),
            "topCourses": self.course_service.get_top_courses()
        }


class AdminPublishRequests(Resource):

    ACCEPT_ACTION = 'accept'
    DECLINE_ACTION = 'decline'

    problem_service = ProblemService()
    user_service = UserService()

    @marshal_with(PublishRequest.api_fields)
    def get(self):
        return self.problem_service.get_all_publish_requests()
    
    @jwt_required
    @verify_attributes(["action"])
    @marshal_with(Problem.api_fields)
    def post(self):
        user_id = get_jwt_identity()
        data = request.get_json()
        pr_id = data.get('id')
        action = data.get('action')
        
        if self.user_service.check_admin(user_id):
            if action == self.ACCEPT_ACTION:
                return self.problem_service.accept_publish_request(pr_id)
            elif action == self.DECLINE_ACTION:
                return self.problem_service.decline_publish_request(pr_id)
            else:
                raise BadRequest("'{}' action is not valid".format(action))
        else:
            raise Unauthorized("User with id {} is not admin".format(user_id))
