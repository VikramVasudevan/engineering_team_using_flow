#!/usr/bin/env python
import datetime
from random import randint
from datetime import time
import random
from typing import Optional
from crewai import Crew
from crewai.flow.flow import router, or_
from pydantic import BaseModel
from crewai.flow import Flow, listen, start
from engineering_team_using_flow.crews.engineering_crew.engineering_crew import (
    CodeReviewFeedback,
    EngineeringCrew,
)


class EngineeringState(BaseModel):
    module_name: str = ""
    business_requirement: str = ""
    technical_design: Optional[str] = ""
    backend_code: Optional[str] = ""
    frontend_code: Optional[str] = ""
    unit_test_code: Optional[str] = ""
    backend_code_review_feedbacks: list[CodeReviewFeedback] = []
    frontend_code_review_feedbacks: list[CodeReviewFeedback] = []

MAX_REVIEW_ITERATIONS = 2
BUSINESS_REQUIREMENTS: list[EngineeringState] = [
    EngineeringState(
        module_name="mod_series_eval",
        business_requirement="Create a web application that  allows the user to evaluate the first N terms of a given series and \
    multiply the total by X (default to 4). for instance, the series could be something like :\
    1 + 1/3 - 1/5 + 1/7 - 1/9 ... ",
    )
]


class EngineeringFlow(Flow[EngineeringState]):

    @start()
    def generate_business_requirement(self):
        print("Generating business requirement")
        chosen_requirement = random.choice(BUSINESS_REQUIREMENTS)
        self.state.business_requirement = chosen_requirement.business_requirement
        self.state.module_name = chosen_requirement.module_name

    @listen(generate_business_requirement)
    def design_product(self):
        print("Designing product for requirement: ", self.state)
        engineeringCrew = EngineeringCrew()

        mycrew = Crew(
            agents=[engineeringCrew.development_lead()],
            tasks=[engineeringCrew.design_task()],
        )
        result = mycrew.kickoff(
            inputs={
                "id" : self.state.id,
                "requirement": self.state.business_requirement,
                "module_name": self.state.module_name,
                "review_comments" : ""
            }
        )

        print("Product Design Created", result.raw)
        self.state.technical_design = result.raw

    @listen(or_("design_product","REWRITE_BACKEND_CODE"))
    def develop_backend(self):
        print("Developing backend : ", self.state)
        engineeringCrew = EngineeringCrew()

        mycrew = Crew(
            agents=[engineeringCrew.backend_engineer()],
            tasks=[engineeringCrew.backend_coding_task()],
        )
        result = mycrew.kickoff(
            inputs={
                "id" : self.state.id,
                "requirement": self.state.business_requirement,
                "module_name": self.state.module_name,
                "review_comments" : self.state.backend_code_review_feedbacks[-1].review_comments_markdown if self.state.backend_code_review_feedbacks else ""
            }
        )

        print("Backend Code Created", result.raw)
        self.state.backend_code = result.raw
        return "BACKEND_CODE_CREATED"

    @router(develop_backend)
    def review_backend_code(self):
        print("Reviewing backend code : ", self.state)
        if(len(self.state.backend_code_review_feedbacks) >= MAX_REVIEW_ITERATIONS):
            return "MAX_REVIEW_ITERATIONS_EXCEEDED"
        engineeringCrew = EngineeringCrew()

        mycrew = Crew(
            agents=[engineeringCrew.code_reviewer()],
            tasks=[engineeringCrew.code_review_task()],
        )
        if self.state.backend_code_review_feedbacks is None:
            self.state.backend_code_review_feedbacks = []

        result = mycrew.kickoff(
            inputs={
                "id" : self.state.id,
                "requirement": self.state.business_requirement,
                "module_name": self.state.module_name,
                "backend_code": self.state.backend_code,
                "iteration" : len(self.state.backend_code_review_feedbacks)
                
            }
        )

        codeReviewFeedback : CodeReviewFeedback = result.tasks_output[0].pydantic # type: ignore[index]
        print(codeReviewFeedback)
        self.state.backend_code_review_feedbacks.append(codeReviewFeedback) 

        if(codeReviewFeedback.passed_review):
            return "BACKEND_CODE_REVIEWED"
        else:
            return "REWRITE_BACKEND_CODE"

    @listen(or_("BACKEND_CODE_REVIEWED", "REWRITE_FRONTEND_CODE"))
    def develop_frontend(self):
        print("Developing frontend : ", self.state)
        engineeringCrew = EngineeringCrew()

        mycrew = Crew(
            agents=[engineeringCrew.frontend_engineer()],
            tasks=[engineeringCrew.frontend_coding_task()],
        )
        result = mycrew.kickoff(
            inputs={
                "id" : self.state.id,
                "requirement": self.state.business_requirement,
                "module_name": self.state.module_name,
                "review_comments" : self.state.frontend_code_review_feedbacks[-1].review_comments_markdown if self.state.frontend_code_review_feedbacks else ""
            }
        )

        print("Frontend Code Created", result.raw)
        self.state.frontend_code = result.raw
        return "FRONTEND_CODE_CREATED"


    @router(develop_frontend)
    def review_frontend_code(self):
        print("Reviewing frontkend code : ", self.state)
        if(len(self.state.frontend_code_review_feedbacks) >= MAX_REVIEW_ITERATIONS):
            return "MAX_REVIEW_ITERATIONS_EXCEEDED"
        engineeringCrew = EngineeringCrew()

        mycrew = Crew(
            agents=[engineeringCrew.code_reviewer()],
            tasks=[engineeringCrew.frontend_code_review_task()],
        )
        if self.state.frontend_code_review_feedbacks is None:
            self.state.frontend_code_review_feedbacks = []

        result = mycrew.kickoff(
            inputs={
                "id" : self.state.id,
                "requirement": self.state.business_requirement,
                "module_name": self.state.module_name,
                "frontend_code": self.state.frontend_code,
                "iteration" : len(self.state.frontend_code_review_feedbacks)
            }
        )

        codeReviewFeedback : CodeReviewFeedback = result.tasks_output[0].pydantic # type: ignore[index]
        print(codeReviewFeedback)
        self.state.frontend_code_review_feedbacks.append(codeReviewFeedback) 

        if(codeReviewFeedback.passed_review):
            return "FRONTEND_CODE_REVIEWED"
        else:
            return "REWRITE_FRONTEND_CODE"

    @listen("FRONTEND_CODE_REVIEWED")
    def write_test_cases(self):
        print("Writing test cases : ", self.state)
        engineeringCrew = EngineeringCrew()

        mycrew = Crew(
            agents=[engineeringCrew.test_engineer()],
            tasks=[engineeringCrew.test_preparation_task()],
        )
        result = mycrew.kickoff(
            inputs={
                "id" : self.state.id,
                "requirement": self.state.business_requirement,
                "module_name": self.state.module_name,
                "backend_code": self.state.backend_code,
                "frontend_code": self.state.frontend_code
            }
        )

        self.state.unit_test_code = result.raw
        return "TEST_CASES_PREPARED"


def kickoff():
    engineering_flow = EngineeringFlow()
    engineering_flow.kickoff()


def plot():
    engineering_flow = EngineeringFlow()
    engineering_flow.plot()


if __name__ == "__main__":
    kickoff()
