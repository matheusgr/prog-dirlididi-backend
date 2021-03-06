from db import db
from models.problem import Problem, Solution, PublishRequest
from exceptions import NotFound

class ProblemService(object):

    def create_problem(self, name, description, tip, tags=None):
        problem = Problem(name=name, description=description, tip=tip)
        if tags:
            problem.add_tags(tags)
        return problem

    def create_publish_request(self, problem):
        p = PublishRequest(problem=problem)
        db.session.add(p)
        return p
    
    def update_problem(self, user_id, key, data):
        problem = self.get_problem_by_key(key)
        if problem.owner != user_id:
            raise Unauthorized("User with id {} is not owner of this problem".format(user_id))
        problem.update(data)
        db.session.commit()
        return problem
    
    def get_publish_request_by_id(self, id):
        publish_request = PublishRequest.query.get(id)
        if publish_request:
            return publish_request
        else:
            raise NotFound("Publish request with id {} was not found".format(id))

    def get_all_publish_requests(self):
        return PublishRequest.query.all()

    def accept_publish_request(self, id):
        publish_request = self.get_publish_request_by_id(id)
        publish_request.accept()
        return publish_request.problem
    
    def decline_publish_request(self, id):
        publish_request = self.get_publish_request_by_id(id)
        publish_request.decline()
        return publish_request.problem

    def get_problem_by_key(self, key):
        problem = Problem.query.get(key)
        if problem:
            return problem
        else:
            raise NotFound("Problem with key {} was not found".format(key))
    
    def get_all(self):
        return Problem.query.all()

    def get_all_public(self, name=None):
        public = [p for p in self.get_all() if p.publish]
        if name:
            public = [p for p in public if name in p.name]
        return public

    def check_response(self, problem, results):
        ''' Returns the test results for a solution '''
        result = ""
        tests = sorted(problem.tests, key=lambda x: x._id)
        results = sorted(results, key=lambda x: int(x.get('id')))

        for i in range(len(results)):
            user_result = results[i]
            key = user_result.get('id')
            user_result = user_result.get('output')
            if int(key) == tests[i]._id:
                if tests[i].output == user_result:
                    result += "."
                else:
                    result += "f"
        return result

    def create_solution(self, user, problem_key, code, tests):
        problem = self.get_problem_by_key(problem_key)
        results = self.check_response(problem, tests)
        solution = Solution(user=user, problem=problem, code=code, tests=tests, result=results, passed="f" not in results)
        db.session.add(solution)
        db.session.commit()
        return solution

    def delete_problem(self, user_id, key):
        problem = self.get_problem_by_key(key)
        problem.delete(user_id)
