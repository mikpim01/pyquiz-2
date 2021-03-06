"""
This file contains all of the views used to control
the pages of pyquiz.
"""

from pyramid.request import Request
from pyramid.httpexceptions import HTTPFound, HTTPSeeOther
from pyramid.renderers import get_renderer

from schema import EditQuestionSchema
from schema import EditShortAnswerQuestionSchema, AddQuestionsSchema

from pyramid.security import authenticated_userid
from pyramid.interfaces import IAuthenticationPolicy

from colander import MappingSchema
from colander import SequenceSchema
from colander import SchemaNode
from colander import String
from colander import Boolean
from colander import Schema
from colander import Date
from colander import Range

from deform import ValidationFailure
from deform import Form
from deform import widget
from deform import FileData
from schema import Questions
from schema import ShortAnswerQuestions

import colander

import deform

from questions import *

from xmlrpclib import ServerProxy
from __init__ import trans, serverLocation

import datetime



def view_create_test(request):
    """
    This is the view for the form page where tests are created.
    """
    if 'user' not in request.session.keys() or 'teacher' not in request.session['user']['roles'] :
        return HTTPFound(location='/')
    main = get_renderer('templates/master.pt').implementation()
    dbsession = DBSession()
    section_id = int(request.GET["id"])
    terms = dbsession.query(Term).filter(
                             Term.section_id == section_id).all()
    choices = []
    for term in terms:
        choices.append((term.term_id, term.term_name))
    class TestSchema(Schema):
        """
        Schema that stores the test being created.
        """
        import datetime
        name = SchemaNode(String())
        term = SchemaNode(
                    String(),
                    widget=widget.SelectWidget(values = choices)
                    )
        attempts = SchemaNode(String())
        start_date =SchemaNode( Date(),
                    validator=Range(
                        min=datetime.datetime.now(),
                        min_err=('${val} is earlier than earliest date ${min}')))
        end_date = SchemaNode( Date(),
                    validator=Range(
                        min=datetime.datetime.now(),
                        min_err=('${val} is earlier than earliest date ${min}')))
        test_type = SchemaNode(String(),
                               widget = widget.SelectWidget(values=
                                                    (('assignment', 'Assignment'),
                                                    ('homework', 'Homework'),
                                                    ('exam', 'Exam')))
                               )
        questions = Questions()
        short_answer_questions = ShortAnswerQuestions()
    schema = TestSchema()
    myform = Form(schema, buttons=('submit',), 
                  use_ajax=True)  #create the form for the page
    if 'submit' in request.POST: # check if the submit button was clicked
        controls = request.POST.items() # get the data from the form
        dbsession = DBSession()
        parse_form_data(controls, section_id, dbsession)
        return HTTPFound(location='/course?id='+str(section_id)) #redirect to homepage
    now = datetime.datetime.now()
    appstruct = {'start_date':now, 'end_date':now, 'terms':choices}
    return {'form':myform.render(appstruct), 'main': main}

def view_add_questions(request):
    """+
    this is the view to add a question to an existing test
    """
    if 'user' not in request.session.keys() or 'teacher' not in request.session['user']['roles'] :
        return HTTPFound(location='/')
    test_id = int(request.GET["id"])
    dbsession = DBSession()
    test = dbsession.query(Test).filter(Test.id==test_id).first()
    answers = dbsession.query(Question).filter(
                                Question.test_id == test.id).all()
    question_num = len(answers)
    post = request.POST
    if 'add questions' in post:
        controls = request.POST.items() # get the data from the form
        parse_add_form_data(controls, dbsession, question_num, test)
        return HTTPFound(location='/edit_test?id='+str(test_id)) 
                                                    #redirect to the tests edit page
    schema = AddQuestionsSchema()
    main = get_renderer('templates/master.pt').implementation()
    myform = Form(schema, buttons=('add questions',), 
                    use_ajax=True)
    return {'form':myform.render(), 'main': main}

def view_change_dates(request): #Untested,because of incomplete
    """
    ###incomplete###
    this is the view to change the start and end dates of an existing test
    """
    main = get_renderer('templates/master.pt').implementation()
    test_id = int(request.GET["id"])
    dbsession = DBSession()
    test = dbsession.query(Test).filter(Test.id==test_id).first()
    post = request.POST
    if 'Change' in post:
        controls = request.POST.items() # get the data from the form
        start_time = str(controls[2][1]).split('-')
        end_time = str(controls[3][1]).split('-')
        start_time = datetime.datetime(int(start_time[0]), int(start_time[1]),int(start_time[2]))
        end_time = (datetime.datetime(int(end_time[0]), int(end_time[1]),int(end_time[2]))
                                                 + datetime.timedelta(hours=23, minutes=59))
        test.start_time = start_time
        test.end_time = end_time
        dbsession.flush()
        return HTTPFound(location='/edit_test?id='+str(test_id))

    from colander import Date, Range
    class ChangeDatesSchema(colander.Schema):
        start_date =SchemaNode( Date(),
                               validator=Range(
                                         min=datetime.date(2010, 5, 5),
                                         min_err=('${val} is earlier than earliest date ${min}')))
        end_date = SchemaNode( Date(),
                               validator=Range(
                                         min=datetime.date(2010, 5, 5),
                                         min_err=('${val} is earlier than earliest date ${min}')))
    schema = ChangeDatesSchema()
    myform = Form(schema, buttons=('Change',), 
                    use_ajax=True)
    now = datetime.datetime.now()
    appstruct = {'start_date':test.start_time, 'end_date':test.end_time}
    return {'form':myform.render(appstruct), 'main': main}
    
def view_edit_question(request):
    """
    this view allows a teacher to edit an existing question in an existing test
    """
    ###load the question number and test id###
    if 'user' not in request.session.keys() or 'teacher' not in request.session['user']['roles'] :
        return HTTPFound(location='/')
    
    test_id = int(request.GET["id"])
    quesiton_num = 1
    try:
        question_num = int(request.GET["question"])
    except:
        question_num = 1

    ###load the test and it's questions and their answers from the database###
    dbsession = DBSession()
    test = dbsession.query(Test).filter(Test.id==test_id).first()
    all_questions = dbsession.query(Question).filter(
                                    Question.test_id==test.id).all()
    total_questions = len(all_questions)
    for q in all_questions:
        if q.question_num == question_num:
            question = q

    post = request.POST
    if 'submit changes' in post:
        controls = post.items()
        parse_edit_form_data(controls, dbsession, question)
        location ='/edit_test?id='+str(test.id)
        return HTTPSeeOther(location=location)
    
    main = get_renderer('templates/master.pt').implementation()
    
    if (question.question_type == "multipleChoice" or
        question.question_type == "selectTrue"):
        all_answers = dbsession.query(Answer).filter(
                                       Answer.question_id==question.id).all()
        answers = []
        for answer in all_answers:
            answers.append({"text":answer.answer,'correct':answer.correct})
        schema = EditQuestionSchema()
        appstruct = {'text':(question.question),'answers':answers}
    if question.question_type == "shortAnswer":
        schema = EditShortAnswerQuestionSchema()
        appstruct = {'text':(question.question)}
    form = Form(schema, buttons=('submit changes',), 
                  use_ajax=True)
    form = form.render(appstruct)
    return {"test":test,'form':form, 'question': question, 'main': main}

def view_delete_test(request):
    """
    This view allows teachers to delete a test in a section they teach
    """
    if 'user' not in request.session.keys() or 'teacher' not in request.session['user']['roles'] :
        return HTTPFound(location='/')
    main = get_renderer('templates/master.pt').implementation()
    test_id = int(request.GET["id"])
    dbsession = DBSession()
    test = dbsession.query(Test).filter(Test.id == test_id).first()
    section = dbsession.query(Section).filter(Section.id == test.course).first()
    post = request.POST
    if 'no' in post:
        return HTTPFound(location='/edit_test?id='+str(test.id))
    if 'yes' in post:
        questions = dbsession.query(Question).filter(
                                    Question.test_id == test.id).all()
        for question in questions:
             answers = dbsession.query(Answer).filter(
                                       Answer.question_id == question.id).all()
             for answer in answers:
                 dbsession.delete(answer)
                 dbsession.flush()
             dbsession.delete(question)
             dbsession.flush()
        dbsession.delete(test)
        dbsession.flush()
        return HTTPFound(location='/')
    message = []
    message.append("Are you sure you want to delete this test?")
    message.append("Test: " + test.name)
    message.append("Course: " + section.course_name)
    class deleteForm(colander.Schema):
        pass
    schema = deleteForm()
    form = deform.Form(schema, buttons=('yes','no'))
    return {'form':form.render(), 'message':message, 'main': main}
    
def view_edit_test(request):
    """
    This view allows a teacher to edit an existing test
    """
    if 'user' not in request.session.keys() or 'teacher' not in request.session['user']['roles'] :
        return HTTPFound(location='/')
    main = get_renderer('templates/master.pt').implementation()
    test_id = int(request.GET["id"]) #get test id

    ###load test and questions from database###
    dbsession = DBSession()
    test = dbsession.query(Test).filter(Test.id==test_id).first()
    all_questions = dbsession.query(Question).filter(
                                    Question.test_id==test.id).all()
    num_questions = len(all_questions)

    delete_link = "/delete_test?id="+str(test.id)
    add_link = "/add_questions?id="+str(test.id)
    change_dates_link = "/change_dates?id="+str(test.id)

    ###create a list of questions, each question will be of the form###
    ###("question #: QUESTION STATUS", "/test?id=#;question#")###
    questions = []
    for i in range(num_questions):
        questions.append(("question "+str(i+1),
                 "/edit_question?id="+str(test_id)+";question="+str(i+1)))
    
    return {"test":test,"questions":questions,
            'delete_link':delete_link,'add_link':add_link,
            "change_dates_link":change_dates_link, 'main': main}

def view_index(request):
    """
    View associated with the home page of the app.
    """
    main = get_renderer('templates/master.pt').implementation()
    if authenticated_userid(request) == None or 'user' not in request.session.keys():
        return HTTPFound(location='/')
    if 'current_test' in request.session.keys():
        request.session.pop('current_test') #remove current_test from session
    userinfo = request.session['user']
    messages = []
    messages.append("Welcome " + userinfo['name'] + " to pyquiz.")
    dbsession = DBSession()
    if authenticated_userid(request) == 'teacher':
        messages.append('You are currently teaching the following classes:')
    if authenticated_userid(request) == 'student':
        messages.append('You are currently enrolled in the following classes:')
    sections = []
    for c in userinfo['courses']:
        section = dbsession.query(Section).filter(
                                 Section.course_id == c).first()
        if section != None:
             sections.append(section)
    messages.append('')
#    if len(courses) == 0:
#        messages[2] == 'You have no classes' ##Depreceated due to SchoolTool integration? 
    for section in sections:
        section.url = 'course?id='+str(section.id)
    return {'messages': messages, 'sections': sections, 'main': main}

def view_ungraded_tests(request):
    """
    This view lets a teacher view all of the instances of a test that have been taken
    and have tests still have questions waiting for teachers to grade.
    """
    if 'user' not in request.session.keys() or 'teacher' not in request.session['user']['roles'] :
        return HTTPFound(location='/')  
    main = get_renderer('templates/master.pt').implementation()
    if "current_test" in request.session.keys():
        request.session.pop('current_test')
    test_id = int(request.GET["id"])
    dbsession = DBSession()
    test = dbsession.query(Test).filter(Test.id==test_id).first()
    taken_tests = dbsession.query(TakenTest).filter(TakenTest.test_id == test_id).all()
    ungraded_tests = []
    for taken_test in taken_tests:
        if taken_test.has_ungraded:
            ungraded_tests.append(taken_test)
            taken_test.url = "grade_submitted_test?id="+str(taken_test.id)
            taken_test.link = "grade test by " + taken_test.student_name
    message = ''
    if len(ungraded_tests) == 0: message = 'There are no tests to grade'
    return {'test': test, 'taken_tests': ungraded_tests, 'message':message, 'main': main}

def view_grade_question(request):
    """
    This view lets a teacher grade a question that can not be graded automatically
    """
    if 'user' not in request.session.keys() or 'teacher' not in request.session['user']['roles'] :
        return HTTPFound(location='/')  
    main = get_renderer('templates/master.pt').implementation()
    if "current_test" in request.session.keys():
        request.session.pop('current_test')
    question_id = int(request.GET["id"])
    dbsession = DBSession()
    answer = dbsession.query(TakenAnswer).filter(TakenAnswer.id==question_id).first()
    question = dbsession.query(Question).filter(Question.id==answer.question_id).first()
    taken_test = dbsession.query(TakenTest).filter(TakenTest.id==answer.takentest_id).first()
    test = dbsession.query(Test).filter(Test.id == taken_test.test_id).first()
    section = dbsession.query(Section).filter(Section.id == test.course).first()
    num_questions = len(dbsession.query(Question).filter(Question.test_id == test.id).all())
    post = request.POST
    if 'correct' in post or 'incorrect' in post:
        if not answer.graded:
            answer.graded = True
            taken_test.number_graded_questions += 1
            dbsession.flush()
        if 'correct' in post and not answer.correct:
            answer.correct = True
            taken_test.correct_graded_questions += 1
            dbsession.flush()
        if 'incorrect' in post and answer.correct:
            answer.correct = False
            taken_test.correct_graded_questions -= 1
            dbsession.flush()
        if taken_test.number_graded_questions == num_questions:
            new_grade = int(((taken_test.correct_graded_questions*1.0)/ num_questions)*100)
            #submit grade to school tool
            server = ServerProxy(serverLocation, transport = trans)
            grade = server.check_grade(test.term_id, section.course_id, 
                                taken_test.username, test.schooltool_id)
            if grade == None or grade < new_grade or grade == '':
                server.submit_grade(test.term_id, section.course_id, 
                                taken_test.username, test.schooltool_id, new_grade)
                taken_test.has_ungraded = False
            return HTTPFound(location='/ungraded_tests?id='+str(test.id))
        return HTTPFound(location='/grade_submitted_test?id='+str(taken_test.id))


    messages = []
    messages.append("Question Number "+str(question.question_num))
    messages.append("Question: "+question.question)
    messages.append(taken_test.student_name+ "'s answer: " + answer.user_answer)
    class gradeForm(colander.Schema):
        pass
    schema = gradeForm()
    form = deform.Form(schema, buttons=('correct','incorrect'))
    return {"message": messages, "form": form.render(), 'main': main}
    
def view_grade_submitted_test(request):
    """
    This view lets a teacher view information on a test that a student has submitted and
    provides links to ungraded questions in the test so the teacher may grade them.
    """
    if 'user' not in request.session.keys() or 'teacher' not in request.session['user']['roles']:
        return HTTPFound(location='/')  
    main = get_renderer('templates/master.pt').implementation()
    if "current_test" in request.session.keys():
        request.session.pop('current_test')
    test_id = int(request.GET["id"])
    dbsession = DBSession()
    taken_test = dbsession.query(TakenTest).filter(TakenTest.id==test_id).first()
    test = dbsession.query(Test).filter(Test.id==taken_test.test_id).first()
    if attempts_remaining(dbsession, test.id, request.session['user']['name']) <= 0:
        return HTTPFound(location='/')
    if (test.start_time - datetime.datetime.now()) > (datetime.timedelta(0)):
        return HTTPFound(location='/')
    if (test.end_time - datetime.datetime.now()) < (datetime.timedelta(0)):
        return HTTPFound(location='/')
    messages = []
    messages.append("Test Name: " + test.name)
    messages.append("Taken by " + taken_test.student_name + " on " + taken_test.time_submitted)
    answers = dbsession.query(TakenAnswer).filter(TakenAnswer.takentest_id == taken_test.id).all()
    for answer in answers:
        if answer.graded:
            answer.html = u'<p>'+str(answer.question_num)+u'. Graded: '
            if answer.correct:
                answer.html += u'Correct</p>'
            else:
                answer.html += u'Incorrect</p>'
        else:
            answer.html = u'<a href="grade_question?id='+str(answer.id)+u'">'+str(answer.question_num)
            answer.html += u'. Not Graded</a>'
    return {'messages':messages, 'answers':answers, 'main': main}
            
def view_course_teacher(request):
    if authenticated_userid(request) == None or 'user' not in request.session.keys():
        return HTTPFound(location='/')
    if 'current_test' in request.session.keys(): 
        request.session.pop('current_test')
    course_id = int(request.GET["id"])
    if authenticated_userid(request) == 'student':
        return HTTPFound(location='/course?id='+str(course_id))
    main = get_renderer('templates/master.pt').implementation()
    dbsession = DBSession()
    section = dbsession.query(Section).filter(Section.id == course_id).first()
    tests = dbsession.query(Test).filter(Test.course == course_id).all() #load all tests
    for test in tests:
        test.edit = "edit_test?id="+str(test.id) 
        taken_tests = dbsession.query(TakenTest).filter(TakenTest.test_id == test.id).all()
        ungraded = False
        for taken_test in taken_tests:
            if taken_test.has_ungraded:
                ungraded = True
        test.url = "ungraded_tests?id="+str(test.id)
        if ungraded:
            taken_tests = dbsession.query(TakenTest).filter(TakenTest.test_id == test.id).all()
            ungraded_tests = 0 
            for taken_test in taken_tests:
                if taken_test.has_ungraded:
                    ungraded_tests +=1
            test.ungraded_tests = ungraded_tests
        else:
            test.ungraded_tests = 0
    #for t in tests:
        #if 'url' not in dir(t):
            #tests.remove(t) #this can never happen - see line 400.  Tests, therefore, are incapable of covering it
    old_tests = []
    current_tests = []
    upcoming_tests = []
    for test in tests:
        if (test.start_time - datetime.datetime.now()) > (datetime.timedelta(0)):
            upcoming_tests.append(test)
        elif (test.end_time - datetime.datetime.now()) < (datetime.timedelta(0)):
            old_tests.append(test)
        else: current_tests.append(test)
    messages = []
    messages.append("Course: "+section.course_name)
    instructors = section.instructor.split('%&')
    m = "Instructor(s): " + instructors[0]
    i = 1
    while i < len(instructors):
        m += ', ' + instructors[i]
        i += 1
    messages.append(m)
    if len(tests) > 0:
        messages.append('There are ungraded tests in the following tests.')
    else: messages.append('There are no tests to grade.')
    link = ('/create_test?id='+str(section.id),
                               'Create A New Test')
    return {'old_tests':old_tests, 'current_tests':current_tests,'upcoming_tests':upcoming_tests,
            'messages':messages, 'link':link, 'main': main}

def view_course(request):
    """
    This view lets a student or a teacher view a course.  To a student it will let them
    take any open tests that they need to take and to a teacher it will provide links to 
    grade tests, create tests, and edit tests.
    """
    if authenticated_userid(request) == None or 'user' not in request.session.keys():
        return HTTPFound(location='/')
    course_id = int(request.GET["id"])
    if authenticated_userid(request) == 'teacher':
        return HTTPFound(location='/course_teacher?id='+str(course_id))
    main = get_renderer('templates/master.pt').implementation()
    if 'current_test' in request.session.keys(): 
        request.session.pop('current_test')
    dbsession = DBSession()
    section = dbsession.query(Section).filter(Section.id == course_id).first()
    tests = dbsession.query(Test).filter(Test.course == course_id).all() #load all tests
    for test in tests:
        test.url = "test?id="+str(test.id) #create url for each test to pass to
                                               #the template
        test.attempts_remaining = attempts_remaining(dbsession, test.id, request.session['user']['name'])
    #for t in tests:
        #if 'url' not in dir(t): ## THIS LINE IS TAUTOLOGICALLY IMPROBABLE. REPAIR!
            #tests.remove(t)
    old_tests = []
    current_tests = []
    upcoming_tests = []
    for test in tests:
        if (test.start_time > datetime.datetime.now()):
            upcoming_tests.append(test)
        elif (test.end_time < datetime.datetime.now()):
            old_tests.append(test)
        else:
            if test.attempts_remaining <= 0:
                old_tests.append(test)
            else:
                current_tests.append(test)
    messages = []
    messages.append("Course: "+section.course_name)
    instructors = section.instructor.split('%&')
    m = "Instructor(s): " + instructors[0]
    i = 1
    while i < len(instructors):
        m += ', ' + instructors[i]
        i += 1
    messages.append(m)
    messages.append('There are '+str(len(tests))+' tests to take:')
    return {'old_tests':old_tests, 'current_tests':current_tests,
            'upcoming_tests':upcoming_tests, 'messages':messages, 'main': main}

def view_question(request):
    """
    The view for the question page to answer a single question of a test.
    """
    if authenticated_userid(request) == None or 'user' not in request.session.keys():
        return HTTPFound(location='/')
    main = get_renderer('templates/master.pt').implementation()
    ###load the question number and test id###
    test_id = int(request.GET["id"])
    quesiton_num = 1
    try:
        question_num = int(request.GET["question"])
    except:
        question_num = 1

    ###load the test and it's questions and their answers from the database###
    dbsession = DBSession()
    test = dbsession.query(Test).filter(Test.id==test_id).first()
    if attempts_remaining(dbsession, test.id, request.session['user']['name']) <= 0:
        return HTTPFound(location='/') #if no more attempts left
    if (test.start_time - datetime.datetime.now()) > (datetime.timedelta(0)):
        return HTTPFound(location='/') #if it's too early to take
    if (test.end_time - datetime.datetime.now()) < (datetime.timedelta(0)):
        return HTTPFound(location='/') #if it's too late to take
    all_questions = dbsession.query(Question).filter(
                                    Question.test_id==test.id).all()
    total_questions = len(all_questions)
    for q in all_questions:
        
        if q.question_num == question_num:
            question = q

    ###create "current_test" in the session object###
    session = request.session
    user_choice = ''
    if "current_test" not in session.keys() or (
                      session["current_test"]["name"] != test.name):
            session["current_test"] = {"name": test.name}

    ###load any previously selected answer to this question###
    if str(question_num) in session['current_test'].keys():
        user_choice = session['current_test'][str(question_num)]

    ###check if a question was submited and put the answer in the session###
    post = request.POST
    if 'review test' in post or 'next question' in post:
        controls = post.items()
        answer = "na"
        i = 0
        if question.question_type == "shortAnswer":
            for control in controls:
                if control[0] == 'answer':
                    answer = str(control[1])
        if question.question_type == "multipleChoice":
            for control in controls:
                if control[0] == 'deformField1':
                    answer = str(control[1])
        if question.question_type == "selectTrue":
            answer = []
            for control in controls:
                if control[0] == 'checkbox':
                    answer.append(control[1])
        session["current_test"][str(question_num)]=answer 
                                            #store selected answer
        if 'next question' in post:
            return HTTPFound(location='/question?id='+str(test.id)+
                             ';question='+str(question_num+1))
        if 'review test' in post: #check if it was the last question
                                  #if so redirect to the test's submit page
            return HTTPFound(location='/test?id='+str(test.id))

    ###create the question's form###
    if question.question_type == "multipleChoice":
        schema = create_multiple_choice_form(question, 
                                       dbsession, user_choice)
    if question.question_type == "selectTrue":
        schema = create_select_all_form(question,
                                       dbsession, user_choice)
    if question.question_type == "shortAnswer":
        schema = create_short_answer_form(question, 
                                        dbsession, user_choice)
    if question_num == total_questions: #check if this is the last question
        form = deform.Form(schema[0],
                           buttons=('review test',))
    else:
        form = deform.Form(schema[0],
                           buttons=('next question',))
    if question.question_type == "shortAnswer":
        return {"test":test,'form':form.render(schema[1]),
                'link':'/test?id='+str(test.id), 'main': main} #if it's a short answer question (returns default value)
    return {"test":test,'form':form.render(), 'link':'/test?id='+str(test.id), 'main': main}

def view_test(request):
    """
    This view displays the submit page that shows and overview of the test
    and allows the test taker to submit the test for grading.
    """
    if authenticated_userid(request) == None or 'user' not in request.session.keys():
        return HTTPFound(location='/')
    main = get_renderer('templates/master.pt').implementation()
    test_id = int(request.GET["id"]) #get test id

    ###load test and questions from database###
    dbsession = DBSession()
    test = dbsession.query(Test).filter(Test.id==test_id).first()
    all_questions = dbsession.query(Question).filter(
                                    Question.test_id==test.id).all()
    num_questions = len(all_questions)
    if attempts_remaining(dbsession, test.id, request.session['user']['name']) <= 0:
        return HTTPFound(location='/')
    if (test.start_time - datetime.datetime.now()) > (datetime.timedelta(0)):
        return HTTPFound(location='/')
    if (test.end_time - datetime.datetime.now()) < (datetime.timedelta(0)):
        return HTTPFound(location='/')

    ###create the "current_test" in session if it is not already there###
    if "current_test" not in request.session.keys():
        request.session["current_test"] = {"name": test.name}
    current_test = request.session["current_test"]

    ###create a list of questions, each question will be of the form###
    ###("question #: QUESTION STATUS", "/test?id=#;question#")###
    questions = []
    for i in range(num_questions):
        if (str(i+1) not in current_test.keys()):
            questions.append(("question "+str(i+1)+": NOT ANSWERED",
                     "/question?id="+str(test_id)+";question="+str(i+1)))
        else:
            if current_test[str(i+1)] == "na":
                questions.append(("question "+str(i+1)+": NOT ANSWERED",
                         "/question?id="+str(test_id)+";question="+str(i+1)))
            else:
                questions.append(("question "+str(i+1)+": Answered",
                         "/question?id="+str(test_id)+";question="+str(i+1)))
    
    return {"test":test,"questions":questions,"link":"/grade?id="+str(test_id), 'main': main}

def view_grade_test(request):
    """
    This view grades tests and reports the grade in the grade page.
    """
    if authenticated_userid(request) == None or 'user' not in request.session.keys():
        return HTTPFound(location='/')
    main = get_renderer('templates/master.pt').implementation()
    
    ###load the test and it's questions froms the database###
    test_id = int(request.GET["id"])
    dbsession = DBSession()
    test = dbsession.query(Test).filter(Test.id==test_id).first()
    section = dbsession.query(Section).filter(Section.id == test.course).first()
    questions = dbsession.query(Question).filter(
                                    Question.test_id==test.id).all()
    num_questions = len(questions)

    ###create the "current_test" in session if it is not already there###
    if "current_test" not in request.session.keys():
        return HTTPFound(location='/test?id='+str(test.id))
    current_test = request.session["current_test"]

    ###grade the test submitted test###
    correct = 0
    num_graded = 0
    taken_tests = dbsession.query(TakenTest).filter(TakenTest.test_id == test.id).all()
    attempts = 1
    for t in taken_tests:
        if t.username == request.session['user']['name']:
            attempts = t.attempts + 1
            taken_test = dbsession.query(TakenTest).filter(TakenTest.id == t.id).first()
            taken_test.attempts = attempts
            dbsession.flush()
            taken_answers = dbsession.query(TakenAnswer).filter(
                                            TakenAnswer.takentest_id == taken_test.id).all()
            for answer in taken_answers:
                dbsession.delete(answer)
                dbsession.flush()
    if attempts == 1:
        taken_test = TakenTest(test.id, request.session['user']['name'], 
                               request.session['user']['name'],  num_graded,
                               correct, False, attempts)

        dbsession.add(taken_test)
        dbsession.flush()
    session = request.session
    question_messages = [] #quesiton_messages will contain reports for the
                           #template about if each quesiton is correct or not
    ungraded_questions = []
    for question in questions:#loop through and grade each question
        if question.graded: num_graded += 1
        q_num = question.question_num
        if str(q_num) in current_test.keys(): #make sure user selected
                                            #an answer to the question
            user_answer=current_test[str(q_num)]
                                            #get users answer for the question
            grade = grade_question(question, dbsession, user_answer)
            if type(user_answer) == type([]):
                for answer in user_answer:
                    takenAnswer = TakenAnswer(taken_test.id, question, answer, question.graded, grade[0])
                    dbsession.add(takenAnswer)
                if len(user_answer) == 0:
                    takenAnswer = TakenAnswer(taken_test.id, question, None, question.graded, grade[0])
            else:
                takenAnswer = TakenAnswer(taken_test.id, question, user_answer, question.graded, grade[0])
                dbsession.add(takenAnswer)
            dbsession.flush()
            if question.graded:
                if grade[0]:
                    correct += grade[1]
                    question_messages.append(str(q_num)+". Correct")
                else: question_messages.append(str(q_num)+". INCORRECT")
            else:
                taken_test.has_ungraded = True
                dbsession.flush()
                question_messages.append(str(q_num)+". Waiting for teacher to grade.")
        else: question_messages.append(str(q_num)+". INCORRECT")

    taken_test.number_graded_questions = num_graded
    taken_test.correct_graded_questions = correct
    dbsession.flush()
    if not taken_test.has_ungraded:
        server = ServerProxy(serverLocation, transport = trans)
        grade = server.check_grade(test.term_id, section.course_id, 
                                   request.session['user']['name'],
                                   test.schooltool_id)
        new_grade = int(((1.0*correct)/num_graded)*100)
        if grade == None or grade < new_grade:
            server.submit_grade(test.term_id, section.course_id, 
                                request.session['user']['name'],
                                test.schooltool_id, new_grade)

    ###create a report to display the result of the test###
    if num_graded > 0:
        message ="You got "+str(correct)+" out of "+str(num_graded)+" correct"
        message =message +"(" + str(int(1000.0*correct/num_graded)/10.0) + "%)."
        message += " This grade only includes automaticly graded questions."
    else:
        message="There were no graded questions."
    session.pop("current_test") #remove "current_test" from sesssion

    return {"test":test, "message":message,"questions":question_messages, 'main': main}
        
                                  
   
