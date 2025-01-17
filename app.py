from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    session,
    jsonify,
    flash,
)

import json
import os
from src.User import User
from flask import send_from_directory
from werkzeug.utils import secure_filename
from src.Database.DatabaseManager import DatabaseManager
from src.Database.Update.CreateAccount import CreateAccount
from src.Database.Update.createCourse import CreateCourse
from src.Database.Query.SelectCourseQuery import SelectCourseQuery
from src.Database.Query.SelectGradeForStudent import SelectGradeForStudent
from src.Database.Query.SelectStudentUserPass import SelectStudentUserPass
from src.Database.Check.UsernamePasswordCheck import UsernamePasswordCheck
from src.Database.Query.SelectRegisteredCoursesQuery import SelectRegisteredCourses
from src.Database.Check.CheckUserIsStudent import CheckUserIsStudent
from src.Database.Check.CheckUserIsInstructor import CheckUserIsInstructor
from src.Database.Query.SelectPeopleInCourse import SelectPeopleInCourse
from src.Database.Query.SelectInstructorsForCourse import SelectInstructorsForCourse
from src.Database.Query.SelectGradesForCourse import SelectGradesForCourse
from src.Database.Query.SelectAssignmentsForCourse import SelectAssignmentsForCourse
from src.Database.Query.SelectQuestionsForCourse import SelectQuestionsForCourse
from src.Database.Query.SelectStudentQuery import SelectStudentQuery
from src.Database.Update.UpdateGrade import UpdateGrade
from src.Database.Update.AddQuizToDatabase import AddQuizToDatabase
from src.Database.Update.AddCourseRequest import AddCourseRequest
from src.Database.Update.ApproveCourseRequest import ApproveCourseRequest
from src.Database.Update.DenyCourseRequest import DenyCourseRequest
from src.Database.Query.GetCourseRequests import CourseRequestManager
from src.Database.Update.UpdateEmail import UpdateEmail
from src.Database.Update.UpdatePassword import UpdatePassword
from src.Search.CourseSearch import CourseSearch
from src.Database.Query.SelectQuestionsForAssignment import SelectQuestionsForAssignment
from src.Database.Check.CheckAssignmentCompletion import CheckAssignmentCompletion
from src.Database.Update.SubmitAssignment import SubmitAssignment
from src.Database.Update.DeleteSolutions import DeleteSolutions
from src.Database.Query.SelectSolutionsForCourse import SelectSolutionsForCourse
from src.Database.Update.AddGrade import AddGrade
from src.Database.Update.DeleteAssignment import DeleteAssignment
from src.Database.Query.SelectAllInstructors import SelectAllInstructors
from src.Database.Update.DeleteGradesForAssignment import DeleteGradesForAssignment
from src.Database.Update.DeleteAllSolutionsForAssignment import (
    DeleteAllSolutionsForAssignment,
)
from src.Database.Query.SelectGradesForAssignment import SelectGradesForAssignment
from src.Database.Check.CheckSubmissionIsGraded import CheckSubmissionIsGraded
from src.Database.Update.AddCourseFile import AddCourseFile
from src.Database.Query.SelectFilesQuery import SelectFilesQuery, RetrieveFileInfoQuery
from src.Database.Update.DeleteCourseFile import DeleteCourseFile
from src.Database.Update.DeleteAllQuestionsForAssignment import (
    DeleteAllQuestionsForAssignment,
)
from src.Database.Query.GetEssayLocation import GetEssayLocation
from src.Database.Update.UpdateSolutionEssay import UpdateSolutionEssay
import mysql

currentUser = None  # Start with no user logged in
app = Flask(__name__)
app.secret_key = "a"

###################Prior to Login Pages##########################

#Home page. If user is logged in, divert to correct home.
@app.route("/")
def home():

    if session.get("userType") == "Student":
        courses = SelectRegisteredCourses.queryAll((session["userId"],))
        return render_template("student/courses.html", courses=courses)
    elif session.get("userType") == "Instructor":
        return teacherHome()
    else:
        return render_template("openEduHome.html")

#Page for users to login as student, teacher, or admin
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    else:
        # Get inputted username and password from user
        username = request.form.get("uname")
        password = request.form.get("password")

        # Check if user exists in database
        validLogin = UsernamePasswordCheck.check((username, password))
        # If exists, bring back to home page, ow stay on login page
        if validLogin:
            return addUserToSession(username, password)
        else:
            error = "Invalid username and password"
            return render_template("login.html", error=error)

#Helper method that adds user to session and saves the user type. Directs home afterwards
def addUserToSession(username, password):
    # Adds username and userId to session
    StudentData = SelectStudentUserPass.query((username, password))
    userId = StudentData[0]
    session["username"] = request.form["uname"]
    session["userId"] = userId
    # Checks for User type and redirect accordingly
    if userId is None:
        return redirect(url_for("home"))
    if CheckUserIsInstructor.check(userId):
        session["userType"] = "Instructor"
        # URL will be /teacher/dashboard once implemented
        return redirect(url_for("home"))
    if CheckUserIsStudent.check(userId):
        session["userType"] = "Student"
        # URL will be /student/dashboard once implemented
        return redirect(url_for("home"))
    else:
        session["userType"] = "Admin"
        # URL will be /admin/dashboard once implemented
        return redirect(url_for("createCourse"))


#Remove all user info from session then go to home page
@app.route("/logout")
def logout():
    # Remove user from session and return to home page
    session.pop("username", None)
    session.pop("userId", None)
    session.pop("userType", None)
    return redirect(url_for("home"))

#Page where user can create an account of their choice
@app.route("/login/createaccount", methods=["GET", "POST"])
def createAccount():
    if request.method == "GET":
        return render_template("accountCreation.html")
    else:  # Post request
        # Update Database with user inputted information
        form = request.form
        try:
            CreateAccount.update(
                (
                    form["accountType"],
                    form["fname"],
                    form["lname"],
                    form["email"],
                    form["password"],
                    form["uname"],
                )
            )
        except mysql.connector.errors.IntegrityError:
            return render_template("accountCreation.html", error="Username")

        # Forward to the login page

        return redirect(url_for("login"))

#Update account details of any user type
@app.route("/account/update", methods=["GET", "POST"])
def updateAccount():
    if request.method == "GET":
        return render_template("updateAccount.html")
    else:
        requestType = request.form["type"]
        # Password update request
        if requestType == "password":
            successful = UpdatePassword.update(
                (session["userId"], request.form["old"], request.form["new"])
            )

            if successful == False:
                return jsonify({"error": "Password Update Failed"}), 400

        # Email update Request
        if requestType == "email":
            successful = UpdateEmail.update((session["userId"], request.form["email"]))

            if successful == False:
                return jsonify({"error": "Email Update Failed"}), 400

        return {}

#######################Student Pages#######################
    
#Get all student info
@app.route("/student/info", methods=["POST"])
def studentInfo():
    # Returns firstname lastname and email to the given user id
    studentInfo = SelectStudentQuery.query((session["userId"],))
    returnData = {
        "firstName": studentInfo[1],
        "lastName": studentInfo[2],
        "email": studentInfo[3],
    }
    return json.dumps(returnData)


#Student viewing grades from a specifc course
@app.route("/student/<courseId>-<courseName>/grades", methods=["GET"])
def seeGrades(courseId, courseName):
    # Query for getting grades for every assignment in a class for a given student
    grades = SelectGradeForStudent.queryAll(
        (
            session["userId"],
            courseId,
        )
    )
    assignments = SelectAssignmentsForCourse.queryAll((courseId,))
    questions = SelectQuestionsForCourse.queryAll((courseId,))
    courses = SelectRegisteredCourses.queryAll((session["userId"],))

    # Go to See Grades page
    return render_template(
        "student/seeGrades.html",
        grades=grades,
        courseName=courseName,
        username=session["username"],
        courseId=courseId,
        assignments=assignments,
        questions=questions,
        courses=courses,
    )

#Students searching courses to request to join
@app.route("/search", methods=["POST", "GET"])
def search():
    if request.method == "GET":
        courses = SelectRegisteredCourses.queryAll((session["userId"],))
        return render_template("student/search.html", courses=courses)
    else:
        searchTerm = request.form["searchTerm"]
        return CourseSearch.search((searchTerm, session["userId"]))

#Files a request to join a course for a student
@app.route("/Course/<courseId>/join", methods=["POST"])
def joinCourse(courseId):
    userId = session["userId"]

    # Student must be signed in to join a course
    if userId == None:
        return redirect(url_for("login"))

    AddCourseRequest.update((userId, courseId))

    return {}


#Students viewing all teachers and students in their class
@app.route("/student/<courseId>-<courseName>/people", methods=["GET"])
def studentCoursePeople(courseId, courseName):
    instructors = SelectInstructorsForCourse.queryAll((courseId,))
    people = SelectPeopleInCourse.queryAll((courseId,))
    courses = SelectRegisteredCourses.queryAll((session["userId"],))

    return render_template(
        "student/people.html",
        courseId=courseId,
        courseName=courseName,
        people=people,
        instructors=instructors,
        courses=courses,
    )

#Student dahsboard that views all courses they are enrolled in
@app.route("/student/<courseId>-<courseName>/dashboard", methods=["GET"])
def courseDashboard(courseId, courseName):
    courses = SelectRegisteredCourses.queryAll((session["userId"],))

    # Retrieve the list of files for the course
    files = SelectFilesQuery.get_files_for_course(courseId)

    return render_template(
        "student/courseDashboard.html",
        courseId=courseId,
        courseName=courseName,
        courses=courses,
        files=files,
    )

#View an essay assignment from teacher
@app.route("/student/essay/<int:courseId>-<int:assignmentId>-<int:studentId>")
def downloadEssay(courseId, assignmentId, studentId):
    file_info = GetEssayLocation.query((courseId, assignmentId, studentId,))

    if file_info:
        file_path = file_info[0]
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        return send_from_directory(directory, filename, as_attachment=True)
    else:
        return "File not found", 404


#View all assignments created by teacher
@app.route("/student/<courseId>-<courseName>/assignments", methods=["GET"])
def seeAssignments(courseId, courseName):
    assignments = SelectAssignmentsForCourse.queryAll((courseId,))
    courses = SelectRegisteredCourses.queryAll((session["userId"],))
    for i in range(0, len(assignments)):
        completion = CheckAssignmentCompletion.check(
            (
                courseId,
                assignments[i][0],
                session["userId"],
            )
        )
        if completion == False:
            completion = (False,)
        else:
            completion = (True,)
        assignments[i] = assignments[i] + completion

    return render_template(
        "student/seeAssignments.html",
        courseId=courseId,
        assignments=assignments,
        courseName=courseName,
        courses=courses,
    )

#Viewing a specific assignment as a student
@app.route(
    "/student/<courseId>-<courseName>/assignments/<assignmentId>-<assignmentName>",
    methods=["GET"],
)
def studentAssignment(courseId, courseName, assignmentId, assignmentName):
    questions = SelectQuestionsForAssignment.queryAll(
        (
            courseId,
            assignmentId,
        )
    )
    completion = CheckAssignmentCompletion.check(
        (
            courseId,
            assignmentId,
            session["userId"],
        )
    )
    # For now, set these to None!
    is_quiz = None
    essay_prompt = None
    # Query the database to check if the assignment is a quiz or an essay
    cursor = DatabaseManager.getDatabaseCursor()
    try:
        
        
        # Determining if the assignment is a quiz or an essay
        cursor.execute("SELECT quiz FROM Assignment WHERE courseId = %s AND assignmentId = %s", (courseId, assignmentId))
        is_quiz = cursor.fetchone()[0]
        
        if is_quiz == 0:
            # Fetching the essay prompt for essays
            cursor.execute(
                "SELECT questionText FROM Question WHERE courseId = %s AND assignmentId = %s AND questionId = 1",
                (courseId, assignmentId)
            )
            essay_prompt = cursor.fetchone()[0]
    except Exception as e:
        print(f"Error: {e}")
    finally:
        DatabaseManager.closeConnection()

    assignmentName = assignmentName.strip('"')
    return render_template(
        "student/assignment.html",
        courseId=courseId,
        courseName=courseName,
        assignmentId=assignmentId,
        assignmentName=assignmentName,
        questions=questions,
        completion=completion,
        essayPrompt=essay_prompt,
        is_quiz=is_quiz
    )

#Students submitting an assignment for a course
@app.route("/submitAssignment", methods=["POST"])
def submitAssignment():
    form = request.form
    courseId = form.get("courseId", "")
    courseName = form.get("courseName", "")
    assignmentId = form.get("assignmentId", "")
    assignmentName = form.get("assignmentName", "")
    questions = SelectQuestionsForAssignment.queryAll(
        (
            courseId,
            assignmentId,
        )
    )

    for question in questions:
        SubmitAssignment.update(
            (
                courseId,
                question[0],
                assignmentId,
                session["userId"],
                form.get(str(question[0]), ""),
            )
        )

    flash("You have submitted this assignment!")
    return redirect(
        url_for(
            "studentAssignment",
            courseId=courseId,
            courseName=courseName,
            assignmentId=assignmentId,
            assignmentName=assignmentName,
        )
    )

#Student submitting their uploaded file for their essay
@app.route("/submitStudentEssay/<int:courseId>/<int:assignmentId>", methods=["POST"])
def submitStudentEssay(courseId, assignmentId):
    # Check if the file is present in the request
    if 'essay_file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['essay_file']

    # If user does not select file, browser also submit an empty part without filename
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Change upload directory here, but honestly I'm done with this project - Anilov :(
        upload_folder = os.path.join('uploads', 'essays', str(courseId), str(session['userId']))
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)

        # Update database
        try:
            cursor = DatabaseManager.getDatabaseCursor()
            # Apparently for essays it should always be 1 so this would be located in the solution...
            questionId = 1
            
            # Check if solution already exists firsts
            check_query = """
                SELECT * FROM Solution WHERE courseId = %s AND assignmentId = %s AND studentId = %s AND questionId = %s
                """
            cursor.execute(check_query, (courseId, assignmentId, session['userId'], questionId))
            if cursor.fetchone():
                # Update existing Solution row if a student has already submitted an essay
                # This prevents duplicate submissions on the same assignment
                update_query = """
                UPDATE Solution SET studentAnswer = %s WHERE courseId = %s AND assignmentId = %s AND studentId = %s AND questionId = %s
                """
                cursor.execute(update_query, (file_path, courseId, assignmentId, session['userId'], questionId))
            else:
                # Insert new Solution row if this is a first submission for the student
                insert_query = """
                INSERT INTO Solution (courseId, questionId, assignmentId, studentId, studentAnswer) VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(insert_query, (courseId, questionId, assignmentId, session['userId'], file_path))
                print("Hello there should be a new solution created with the following", courseId,assignmentId, session['userId'], file_path)

            DatabaseManager.commit()
            flash('File successfully uploaded')
        except Exception as e:
            print(f"Error updating database: {e}")
            flash('An error occurred while uploading the file.')
        finally:
            DatabaseManager.closeConnection()

        
        courseName = request.form.get("courseName", "")
        # Redirects back to list of assignments once submitted successfully
        return redirect(url_for('seeAssignments', courseId=courseId, courseName=courseName))
    
    flash('Invalid file')
    return redirect(request.url)

# This is for checking if file extensions are valid
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



#Student deleting their submission
@app.route("/deleteSolutions", methods=["POST"])
def deleteSolutions():
    form = request.form
    courseId = form.get("courseId", "")
    courseName = form.get("courseName", "")
    assignmentId = form.get("assignmentId", "")
    assignmentName = form.get("assignmentName", "")

    graded = CheckSubmissionIsGraded.check(
        (
            courseId,
            assignmentId,
            session["userId"],
        )
    )
    if graded == False:
        DeleteSolutions.update(
            (
                courseId,
                assignmentId,
                session["userId"],
            )
        )
    else:
        flash("Sorry. This assignment has already been graded.")
    return redirect(
        url_for(
            "studentAssignment",
            courseId=courseId,
            courseName=courseName,
            assignmentId=assignmentId,
            assignmentName=assignmentName,
        )
    )

############################Teacher Pages############################

#Page where teacher can create quizzes
@app.route(
    "/teacher/<courseId>-<courseName>/assignments/createQuiz", methods=["POST", "GET"]
)
def createQuiz(courseId, courseName):
    if request.method == "GET":
        courses = SelectCourseQuery.query((session["userId"],))
        return render_template(
            "teacher/createQuiz.html",
            courseId=courseId,
            courseName=courseName,
            courses=courses,
        )
    elif request.method == "POST":
        questionForm = request.form
        # Retrieve the 'isQuiz' value from form data
        is_quiz = questionForm.get("isQuiz", "0")
        
        if is_quiz == "1":
            # Process quiz creation
            AddQuizToDatabase.update(questionForm, courseId, is_quiz)
        else:
            # Process essay creation
            essay_name = request.form.get("quizId")
            essay_prompt = request.form.get("questionText1")
            create_essay_assignment(courseId, essay_name, essay_prompt)
            
            

        return redirect(
            url_for(
                "teacherCourseAssignments", courseId=courseId, courseName=courseName
            )
        )

#Helper method to create an essay for students
def create_essay_assignment(courseId, essay_name, essay_prompt):
    cursor = DatabaseManager.getDatabaseCursor()
    try:
        # Insert a new record into the Assignment table
        assignment_query = "INSERT INTO Assignment (courseId, name, quiz) VALUES (%s, %s, 0)"
        cursor.execute(assignment_query, (courseId, essay_name))
        assignmentId = cursor.lastrowid  # Get the ID of the newly inserted assignment
        # Insert a corresponding record into the Question table
        question_query = "INSERT INTO Question (questionId, courseId, assignmentId, questionText, longQuestion) VALUES (1, %s, %s, %s, 1)"
        cursor.execute(question_query, (courseId, assignmentId, essay_prompt))
        DatabaseManager.commit()
        
    except Exception as e:
        print(f"Error creating essay assignment: {e}")
    finally:
        DatabaseManager.closeConnection()


#Main Homepage for teachers to see all courses they teach
@app.route("/teacher/homepage", methods=["POST", "GET"])
def teacherHome():
    # temporarily getting a list of all courses
    courses = SelectCourseQuery.query((session["userId"],))

    return render_template("teacher/homepage.html", courses=courses)


#Teacher dashboard of a course they teach. Here they can upload lecture slides and course files for students
@app.route("/teacher/<courseId>-<courseName>/dashboard", methods=["GET", "POST"])
def teacherCourseDash(courseId, courseName):
    courses = SelectCourseQuery.query((session["userId"],))
    if request.method == "POST":
        # Handle file uploads
        file = request.files["file"]
        # Retrieves custom file name from the pop-up window
        custom_file_name = request.form["fileName"]
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join("uploads/course_" + str(courseId), filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)

            # Use AddCourseFile to insert the file record
            AddCourseFile.insert_file_record(courseId, file_path, custom_file_name)

    # Retrieve the list of files for the course to display
    files = SelectFilesQuery.get_files_for_course(courseId)

    return render_template(
        "teacher/courseDashboard.html",
        courseId=courseId,
        courseName=courseName,
        courses=courses,
        files=files,  # Pass the list of files to the template
    )

#Teachers downloading a file 
@app.route("/download_file/<int:file_id>")
def download_file(file_id):
    # Assuming RetrieveFileInfoQuery.get_file_info fetches file path using file_id
    file_info = RetrieveFileInfoQuery.get_file_info(file_id)
    if file_info:
        file_path = file_info["fileLocator"]
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        return send_from_directory(directory, filename, as_attachment=True)
    else:
        return "File not found", 404


#Deleting a file from a course
@app.route("/delete_file/<int:courseId>/<courseName>/<int:file_id>", methods=["POST"])
def delete_file(courseId, courseName, file_id):
    success = DeleteCourseFile.delete_file_record(file_id)
    if success:
        flash("File deleted successfully", "success")
    else:
        flash("File could not be deleted", "error")
    return redirect(
        url_for("teacherCourseDash", courseId=courseId, courseName=courseName)
    )  # Redirect to the appropriate page


#View all assignments as a teacher
@app.route("/teacher/<courseId>-<courseName>/assignments", methods=["GET"])
def teacherCourseAssignments(courseId, courseName):
    assignments = SelectAssignmentsForCourse.queryAll((courseId,))
    courses = SelectCourseQuery.query((session["userId"],))
    return render_template(
        "teacher/assignmentsTab.html",
        courseId=courseId,
        courseName=courseName,
        assignments=assignments,
        courses=courses,
    )

#Grading page for teachers to mark assignments from students
@app.route("/teacher/<courseId>-<courseName>/grading", methods=["GET"])
def teacherCourseGrading(courseId, courseName):
    assignments = SelectAssignmentsForCourse.queryAll((courseId,))
    grades = SelectGradesForCourse.queryAll((courseId,))
    questions = SelectQuestionsForCourse.queryAll((courseId,))
    solutions = SelectSolutionsForCourse.queryAll((courseId,))
    courses = SelectCourseQuery.query((session["userId"],))

    # Assures that every index in grades matches solutions, and if the grade doesn't exist, insert a 0 into the correct spot

    if len(grades) < len(solutions):
        for i in range(0, len(solutions)):
            matching = False
            for j in range(0, len(grades)):
                if grades[j] != 0:
                    if (
                        grades[j][0] == solutions[i][0]
                        and grades[j][4] == solutions[i][2]
                        and grades[j][5] == solutions[i][1]
                    ):
                        matching = True
            if matching == False:
                try:
                    grades.insert(i, 0)
                except:
                    grades.append(0)

    return render_template(
        "teacher/grading.html",
        courseId=courseId,
        solutions=solutions,
        courseName=courseName,
        grades=grades,
        assignments=assignments,
        questions=questions,
        courses=courses,
    )


#Updates any grades changes made by teachers
@app.route("/updateGrade", methods=["POST"])
def updateGrade():
    form = request.form
    # If grade is already in database, update it. If not, insert it.
    if form["insert"] == "1":
        AddGrade.update(
            (
                form["courseId"],
                form["questionId"],
                form["assignmentId"],
                form["studentId"],
                session["userId"],
                form["grade"],
            )
        )
    else:
        UpdateGrade.update(
            (
                form["grade"],
                form["courseId"],
                form["questionId"],
                form["assignmentId"],
                form["studentId"],
            )
        )
    return "DONE"

#Teachers viewing all students enrolled in their class
@app.route("/teacher/<courseId>-<courseName>/people", methods=["GET"])
def teacherCoursePeople(courseId, courseName):
    instructors = SelectInstructorsForCourse.queryAll((courseId,))
    people = SelectPeopleInCourse.queryAll((courseId,))
    courses = SelectCourseQuery.query((session["userId"],))
    return render_template(
        "teacher/people.html",
        courseId=courseId,
        courseName=courseName,
        people=people,
        instructors=instructors,
        courses=courses,
    )



#Delete an assignment from the database. Deletes all user submissions as well
@app.route("/deleteAssignment", methods=["POST"])
def deleteAssignment():
    form = request.form
    courseId = form.get("courseId", "")
    courseName = form.get("courseName", "")
    assignmentId = form.get("assignmentId", "")

    DeleteGradesForAssignment.update((courseId, assignmentId,))
    DeleteAllSolutionsForAssignment.update((courseId,assignmentId,))
    DeleteAllQuestionsForAssignment.update((courseId,assignmentId,))
    DeleteAssignment.update((courseId,assignmentId,))

    return redirect(
        url_for("teacherCourseAssignments", courseId=courseId, courseName=courseName)
    )


#Teacher page for viewing a student's assignment
@app.route(
    "/teacher/<courseId>-<courseName>/assignments/<assignmentId>-<assignmentName>/<studentId>-<firstName>-<lastName>",
    methods=["GET"],
)
def teacherAssignment(
    courseId, courseName, assignmentId, assignmentName, studentId, firstName, lastName
):
    questions = SelectQuestionsForAssignment.queryAll(
        (
            courseId,
            assignmentId,
        )
    )
    completion = None
    grades = None
    # If clicked from grading tab, get the completion status and the grades from that submission
    if studentId != "False":
        completion = CheckAssignmentCompletion.check(
            (
                courseId,
                assignmentId,
                studentId,
            )
        )
        grades = SelectGradesForAssignment.queryAll(
            (
                courseId,
                assignmentId,
                studentId,
            )
        )
        # Make grades the same length as solutions as to not cause any errors
        if len(grades) < len(completion):
            for i in range(len(grades) - 1, len(completion)):
                grades.append(0)

    # If assignment is not complete, return to grading page (very unlikely event as the submission won't show up unless it's complete)
    if completion == False:
        flash("This student has not submitted this assignment yet.")
        return redirect(
            url_for(
                "teacherCourseGrading",
                _anchor=str(assignmentId),
                courseId=courseId,
                courseName=courseName,
            )
        )
    else:
        return render_template(
            "teacher/teacherAssignment.html",
            studentId=studentId,
            courseId=courseId,
            grades=grades,
            firstName=firstName,
            lastName=lastName,
            courseName=courseName,
            assignmentId=assignmentId,
            assignmentName=assignmentName,
            questions=questions,
            completion=completion,
        )


########################Admin Pages###############################
    
#Page where admin can accept or deny students into courses
#Get will display the page itself. When clicking accept or deny, the page will run
#a post to itself to run the query to accept/dent student.
@app.route("/admin/approveRegistration", methods=["POST", "GET"])
def courseRegistration():
    if request.method == "GET":
        course_requests = CourseRequestManager.get_course_requests()
        return render_template(
            "admin/approveRegistration.html", course_requests=course_requests
        )
    else:
        type = request.form["type"]

        if type == "approve":
            ApproveCourseRequest.update(
                (request.form["studentId"], request.form["courseId"])
            )

        if type == "deny":
            DenyCourseRequest.update(
                (request.form["studentId"], request.form["courseId"])
            )

        return {}

#Page where admins can create courses and assign them to teachers
@app.route("/admin/createCourse", methods=["POST", "GET"])
def createCourse():
    if request.method == "POST":
        # Extract form data using .get() to avoid BadRequestKeyError
        form = request.form
        courseName = form.get("courseName", "")
        description = form.get("description", "")
        credits = int(form.get("credits", 0))
        session = int(form.get("session", 0))
        term = int(form.get("term", 0))
        instructorId = int(form.get("instructor", 0))

        courseData = (courseName, description, credits, session, term)
        # Update Database with course information
        try:
            CreateCourse.update(courseData, instructorId)
            flash("Course created successfully!", "success")
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "error")
            return render_template("admin/createCourse.html")

        return redirect(url_for("createCourse"))
    else:
        instructorIds, instructorNames = SelectAllInstructors.queryAll()
        return render_template(
            "admin/createCourse.html",
            instructorIds=instructorIds,
            instructorNames=instructorNames,
            len=len,
        )

if __name__ == "__main__":
    app.debug = True
    app.run()
