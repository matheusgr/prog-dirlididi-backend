from db import db
from models.problem import Problem


class ProblemService(object):

    def create_problem(self, name, description, tip, publish):
        problem = Problem(name=name, description=description, tip=tip, publish=publish)
        return problem

    def get_exercise_by_key(self, key):
        return Problem.query.get(key)
    
    def get_all(self):
        return Problem.query.all()
