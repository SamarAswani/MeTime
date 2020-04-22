#IMPORTS
import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify, url_for
from flask_session import Session
from tempfile import mkdtemp
from helpers import login_required
import datetime
from datetime import date, datetime, time, timedelta
import hashlib

app = Flask(__name__) #APPLICATION CREATED

#WEEKDAY CONSTANTS
weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
weekdays2= ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

#APPLICATION SESSION BEING CREATED
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#CONNECTION TO DATABASE BEING ESTABLISHED
db = SQL("sqlite:///data.sqlite")

#This function hashes password using sha224. This hashlib library is used for this
def hash_password(password):
    return(hashlib.sha224(password.encode('utf-8')).hexdigest())

#This function checks the password entered against the hashed password in the database
#and returns a boolean value
def check_password(hashed_password, user_password):
    user_password = hashlib.sha224(user_password.encode('utf-8')).hexdigest()
    return (user_password == hashed_password)


@app.route("/login",methods=['POST','GET'])
def login():
    session.clear()
    if request.method == "POST":
        email = request.form.get("email")
        p = request.form.get("password")
        #If the data is posted request.form.get requests for the email and password entered on the html form
        rows=db.execute("SELECT * FROM Users WHERE Email = :email",email=email)
        if rows == []:
            return render_template("Login.html", error= "Email not registered")
        #Checks if email exists in users table, if not renders template with error message

        else:
            if check_password(rows[0]["Password"], p):
                session["user_id"] = rows[0]["UserID"]
                #if the password entered matches the password in the database then a session is started for the user's account
                tasks = db.execute("SELECT * FROM Tasks WHERE UserID = :userid", userid=session["user_id"])
                SignUpCompleted = db.execute("SELECT SignUpCompleted FROM Users WHERE UserID = :userid", userid=session["user_id"])
                if SignUpCompleted[0]['SignUpCompleted'] == 1:
                    if tasks == []:
                        flash("Please enter some tasks.")
                        return redirect("/EditTasks")
                    else:
                        return redirect("/timetableCreate")
                #If the user has completed the sign up process but has no tasks they will be redirected to the tasks page with the appropriate error messages
                #If the user has tasks then they will be redirected to their timetable
                else:
                    return redirect("/UserPreferences")
                    #If the user has not completed the sign up process they will be redirected to the start of it
            else:
                return render_template("LogIn.html", error= "Incorrect Password")
            #if the passwords do not match then the page will be rendered again with the appropriate error

    else:
        return render_template("LogIn.html")
        #renders log in page when he function is called.


@app.route("/subject",methods=['POST','GET'])
@login_required
def subject():
    if request.method == "POST":
        tempSub =""
        tempCol =""
        subject =[request.form.get("subject")]
        colour = [request.form.get("colour")]
        for i in range (1,11):
            tempSub = request.form.get("subject"+str(i))
            tempCol = request.form.get("colour"+str(i))
            if tempSub != None and tempCol != None:
                subject.append(tempSub)
                colour.append(tempCol)
            else:
                break
        #Puts inputs into arrays so they can be inserted into database later
        for i in range(len(subject)):
            tempSub = subject[i]
            tempCol = colour[i]
            db.execute("INSERT INTO Subjects (SubjectID,SubjectName,Colour,UserID) VALUES (NULL, :tempSub, :tempCol, :userid);",tempSub=tempSub,tempCol=tempCol,userid =session["user_id"])
        #Iterates through arrays created and inserts them into database
        SignUpCompleted = db.execute("SELECT SignUpCompleted FROM Users WHERE UserID = :userid", userid=session["user_id"])
        UserPreferences = db.execute("SELECT * FROM UserInfo WHERE UserID = :userid", userid=session["user_id"])

        if (SignUpCompleted[0]['SignUpCompleted'] == 0) and UserPreferences==[]:
            return redirect("/UserPreferences")
        #If the sign up is incomlete and the user preferences page hasnt been filled out it will redirect the user to the user preferences page
        elif SignUpCompleted[0]['SignUpCompleted'] == 0:
            db.execute("INSERT INTO Subjects (SubjectID,SubjectName,Colour,UserID) VALUES (NULL, 'Other', 'ECEBEB', :userid);",userid =session["user_id"])
            db.execute("UPDATE Users SET SignUpCompleted = 1 WHERE UserID = :userid", userid=session["user_id"])
            return redirect("/tasks")
            #If all the pages have been filled out and the sign up process still hasn't been completed then the SignUpCompleted variable is updated to 1

        else:
            return redirect("/timetableCreate")
        #If the sign up process has been completed the user is redirected to the timetable create page

    else:
        return render_template("Subjects.html")

@app.route("/UserPreferences",methods=['POST','GET'])
@login_required
def UserPreferences():
    if request.method == "POST":
        blockDuration= request.form.get("duration")
        EorL = int(request.form.get("EorL"))
        if EorL >= 7 or EorL <=0:
            return render_template("UserPreferences.html", error="Number of days for Early and Late priority must be between 1 and 7")
        #if Early or Late days preference is more than 7 or less than or equal to 0 then an error will be displayed
        db.execute("DELETE FROM UserInfo WHERE UserID=:userid", userid=session["user_id"])
        #delete all previous data in the tables for the user
        db.execute("INSERT INTO UserInfo (UserID,DurationOfBlocks,EorLDays,CurrentTime) VALUES (:userid, :blockDuration, :EorL, 0);",userid =session["user_id"],blockDuration=blockDuration, EorL=EorL)
        SignUpCompleted = db.execute("SELECT SignUpCompleted FROM Users WHERE UserID = :userid", userid=session["user_id"])
        if SignUpCompleted[0]['SignUpCompleted'] == 1:
            return redirect("/timetableCreate")
        else:
            return redirect("/DayTimes")
        #If sign up is not complete then user is redirected to DayTimes and if it is they are redirected to the timetable
    else:
        return render_template("UserPreferences.html")


@app.route("/DayTimes",methods=['POST','GET'])
@login_required
def DayTimes():
    if request.method == "POST":
        wakeUp=[]
        sleep=[]
        for i in range (1,8):
            wakeUp.append(request.form.get("wakeup"+str(i)))
            sleep.append(request.form.get("sleep"+str(i)))
        #takes all the inputs for wakeup and sleep and puts them in an array
        db.execute("DELETE FROM DayTimes WHERE UserID=:userid", userid=session["user_id"])
        #deletes all previous data in the table for the user
        for i in range(7):
            db.execute("INSERT INTO DayTimes (DayTimesID, UserID, Day, WakeUp, Sleep) VALUES (NULL, :userid, :day, :wakeup, :sleep);",userid=session["user_id"], day=weekdays[i], wakeup=wakeUp[i], sleep=sleep[i])
        return redirect("/UserTimes")
        #inserts data into database and redirects to UserTimes

    else:
        return render_template("DayTimes.html")

@app.route("/UserTimes",methods=['POST','GET'])
@login_required
def UserTimes():
    if request.method == "POST":
        db.execute("DELETE FROM UserTimes WHERE UserID=:userid", userid=session["user_id"])
        #deletes previous usertimes inputs in the database for that user
        arr= request.get_json()
        available = arr["jsonArr"][0]
        preferred = arr["jsonArr"][1]
        #using json to request the inputs sent by the ajax call in the UserTimes.html page
        for t in available:
            for day in weekdays:
                if day in t:
                    t = t[len(day):]
                    StartTime = t[:5]
                    EndTime = t[-5:]
                    db.execute("INSERT INTO UserTimes (TimesID, UserID, DayOfTheWeek, StartTime, EndTime, AorP) VALUES (NULL, :userid, :day, :st, :et, 'A');", userid=session["user_id"], day=day, st=StartTime, et=EndTime)
#looping through the inputs recieved for available time then formatting the string and splitting it up into start time and end time so it can be inputted into the database


        for t in preferred:
            for day in weekdays:
                if day in t:
                    t = t[len(day):]
                    StartTime = t[:5]
                    EndTime = t[-5:]
                    db.execute("INSERT INTO UserTimes (TimesID, UserID, DayOfTheWeek, StartTime, EndTime, AorP) VALUES (NULL, :userid, :day, :st, :et, 'P');", userid=session["user_id"], day=day, st=StartTime, et=EndTime)
        #same is done for the preferred times array

        SignUpCompleted = db.execute("SELECT SignUpCompleted FROM Users WHERE UserID = :userid", userid=session["user_id"])

        if (SignUpCompleted[0]['SignUpCompleted'] == 1) :
            return redirect("/timetableCreate")

        else:
            return redirect("/subject")
#if the sign up process has been completed the user is redirected to the timetable and if not they are redirected to the subjects page

    else:
        duration  = db.execute("SELECT DurationOfBlocks FROM UserInfo WHERE UserID=:userid;",userid=session["user_id"])
        duration = duration[0]["DurationOfBlocks"]
        dayTimes={"Sunday":[],"Monday":[],"Tuesday":[],"Wednesday":[],"Thursday":[],"Friday":[],"Saturday":[]}
#creating a dictionary of all the days of the week to create all the times that need to be displayed on the page

        i=0
        sleepSchedule = db.execute("SELECT * FROM DayTimes WHERE UserID=:userid;",userid=session["user_id"])
        #getting day time inputs from the database
        for item in sleepSchedule:
            if item["Day"] == weekdays[i]:
                nextdaytimes = ["00:00", "01:00", "02:00", "03:00", "04:00", "05:00", "06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00"]
                #if these times are entered as sleep times the application will consider them times in the next day as they are in the morning
                wakeup= item["WakeUp"]
                sleep = item["Sleep"]
                if sleep in nextdaytimes:
                    sleep = datetime.combine(date.today(), time(int(sleep[:2]), int(sleep[3:])))
                    sleep += timedelta(days=1)
                #adds a day to time if it is in nextdaytimes

                else:
                    sleep = datetime.combine(date.today(), time(int(sleep[:2]), int(sleep[3:])))
                dt = datetime.combine(date.today(), time(int(wakeup[:2]), int(wakeup[3:])))
                dayTimes[weekdays[i]].append(dt.strftime("%H:%M"))
                #formating the waking time and adding it to its corresponding weekday array in the day times array (2D array)
                while dt < sleep:
                    dt += timedelta(minutes=duration)
                    dayTimes[weekdays[i]].append(dt.strftime("%H:%M"))
                #adding the duration selected in user preferences to the waking time and appending that result to the array
                #this creates a list of times which are then displayed

            i+=1
        for day in dayTimes:
            times = dayTimes[day]
            for i in range (len(times)):
                if i==0:
                    continue
                else:
                    times[i-1] = times[i-1]+"-"+times[i]
            dayTimes[day] = times[:-1]
            #iterates through times and joins wake time and sleep times into one variable while putting a ':' in the middle
            #this is so they look like this - '08:00-09:00'

        SignUpCompleted = db.execute("SELECT SignUpCompleted FROM Users WHERE UserID = :userid", userid=session["user_id"])

        if (SignUpCompleted[0]['SignUpCompleted'] == 1) :
            redirectPage="http://localhost:5000/timetableCreate"

        else:
            redirectPage="http://localhost:5000/subject"

        return render_template("UserTimes.html",dayTimes=dayTimes, redirectPage=redirectPage)
        #sets rediretPage to the url for timetable if sign up process is complete and if not to the url for the subject pages
        #this link needs to be sent to UserTimes as in order to redirect a page with an ajax call it also needs to be done
        #from the html page - you can see this in the UserTimes.html code

@app.route("/tasks",methods=['POST','GET'])
@login_required
def tasks():
    if request.method == "POST":
        i =1
        tempTask = ""
        task = [request.form.get("task")]
        subject = [request.form.get("subject")]
        DueDate = [request.form.get("DueDate")]
        duration = [request.form.get("duration")]
        priority = [request.form.get("priority")]
        while tempTask != None:
            tempTask= request.form.get("task"+str(i))
            task.append(tempTask)
            subject.append((request.form.get("subject"+str(i))))
            DueDate.append((request.form.get("DueDate"+str(i))))
            duration.append((request.form.get("duration"+str(i))))
            priority.append((request.form.get("priority"+str(i))))
            i+=1
        #adding all the inputs from the tasks entered to different arrays
        for i in DueDate:
            if i == None:
                continue
            dateTemp = datetime.strptime(i,"%Y-%m-%d").date()
            today = date.today()
            if today>dateTemp:
                subjects  = db.execute("SELECT SubjectName FROM Subjects WHERE UserID=:userid;",userid=session["user_id"])
                return render_template("tasks.html", subjects= subjects, error="Deadline must be in the future.")
            if (abs((dateTemp - today).days))>31:
                subjects  = db.execute("SELECT SubjectName FROM Subjects WHERE UserID=:userid;",userid=session["user_id"])
                return render_template("tasks.html", subjects= subjects, error="Deadline is too far away")
            #checking if each due date entered is before the current date or more than a month after it
            #if they are the template is rendered again and the appropriate error message is shown
        for i in range(len(task)-1):
            subjectID = db.execute("SELECT SubjectID FROM Subjects WHERE SubjectName=:subject AND UserID=:userid", subject=subject[i],userid=session["user_id"])
            db.execute("INSERT INTO Tasks (TaskID,UserID,SubjectID,TaskName,Deadline,DurationOfTask,Priority) VALUES (NULL, :userid, :subjectid, :taskname, :duedate, :durationoftask, :priority);",userid =session["user_id"],subjectid=subjectID[0]['SubjectID'],taskname=task[i],duedate=DueDate[i],durationoftask=duration[i],priority=priority[i])
        #getting the subjectID name from the database so that it can be inserted into the tasks table
        return redirect("/timetableCreate")


    else:
        subjects  = db.execute("SELECT SubjectName FROM Subjects WHERE UserID=:userid;",userid=session["user_id"])
        return render_template("tasks.html", subjects = subjects)
        #getting the subject names and sending it to the html page so that the user is able to choose which subject the task is for

@app.route("/register",methods=['POST','GET'])
def register():
    if request.method == "POST":
        fn = request.form.get("FirstName")
        ln = request.form.get("LastName")
        email = request.form.get("email")
        p = request.form.get("password")
        rep = request.form.get("RepeatPassword")
        #getting inputs and storing them in variables
        emails = db.execute("SELECT Email FROM Users")

        if p != rep:
            return render_template("register.html", error="Passwords do not match")
        elif len(p) < 8:
            return render_template("register.html", error="Passwords must be greater than or equal to 8 characters")
        elif ' ' in p:
            return render_template("register.html", error="Passwords cannot contain spaces")
        elif (db.execute("SELECT * FROM Users WHERE Email = :email", email = email)) != []:
            return render_template("register.html", error="Email already in use")

        #checking if passwords dont match, if password is greater than 8 chars, if password contains spaces
        #and if the email is already being used
        #the corresponding error message is displayed if any of these conditions are met
        else:
            password = hash_password(p)
            db.execute("INSERT INTO `Users` (`FirstName`, `LastName`, `Email`, `Password`,'SignUpCompleted','UserID') VALUES (:fn, :ln, :email, :p, 0,NULL);",fn=fn,ln=ln,email=email,p=password)

            flash('Account registered')
            return redirect("/login")
            #if the password is valid then it is hashed and entered into the database
            #the user is then redirected back to the log in page

    else:
        return render_template("register.html")


def days_between(d1, d2):
    d1 = datetime.strptime(d1, "%Y-%m-%d")
    d2 = datetime.strptime(d2, "%Y-%m-%d")
    return abs((d2 - d1).days)
#finds the difference between two days

@app.route("/timetableCreate",methods=['POST','GET'])
@login_required
def timetableCreate():
    DurationAndTasks = db.execute ("SELECT DurationOfBlocks, TaskID FROM UserInfo, Tasks WHERE UserInfo.UserID= :userid AND Tasks.UserID= :userid;", userid=session["user_id"])
    if DurationAndTasks == []:
        duration = db.execute("SELECT DurationOfBlocks FROM UserInfo Where UserID =:userid;", userid=session["user_id"])[0]["DurationOfBlocks"]
        if duration == []:
            flash('Complete Sign Up process')
            return redirect(url_for("UserPreferences"))

    else:
        duration = DurationAndTasks[0]["DurationOfBlocks"]

    for i in DurationAndTasks:
        del i["DurationOfBlocks"]
    taskIDs = DurationAndTasks
    for i in taskIDs:
        db.execute("DELETE FROM Slot WHERE TaskID = :taskid", taskid= i["TaskID"])

    weekdays2= ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

    OutdatedTasks()

    tasks = db.execute("SELECT * FROM Tasks WHERE UserID = :userid", userid=session["user_id"])
    if tasks == []:
        #return redirect(url_for("tasks", error="You currently have no tasks. Please add some."))
        flash('You currently have no tasks. Please add some.')
        return redirect(url_for("tasks"))


    maxArr=[]
    for task in tasks:
        maxArr.append(datetime.strptime(task["Deadline"],"%Y-%m-%d").date())
    maxDate = max(maxArr)
    tempDate = date.today()
    dif = days_between(str(tempDate),str(maxDate))
    calendar={}
    for i in range(dif+1):
        calendar[tempDate.strftime("%Y-%m-%d")] =[]
        tempDate += timedelta(days=1)

    #duration  = db.execute("SELECT DurationOfBlocks FROM UserInfo WHERE UserID=:userid;",userid=session["user_id"])


    for day in calendar:
        dayoftheweek = weekdays2[datetime.strptime(day,"%Y-%m-%d").date().weekday()]
        slots = db.execute("SELECT * FROM UserTimes WHERE DayOfTheWeek = :dayoftheweek AND UserID = :userid", userid=session["user_id"], dayoftheweek=dayoftheweek)
        for slot in slots:
            calendar[day].append({"StartTime":slot["StartTime"], "EndTime":slot["EndTime"], "Duration":duration, "task":"", "TaskID":"", "type":slot["AorP"]})

    for task in tasks:
        dateDue = datetime.strptime(task["Deadline"],"%Y-%m-%d").date()
        todayVar = date.today()
        daysRemaining = (dateDue - todayVar).days
        totalTime = int(task["DurationOfTask"])
        if task["Priority"]=="scattered":
            timePerDay = int(totalTime/daysRemaining)
            timeTemp = timePerDay
            daysTemp = daysRemaining
            for day in calendar:
                daysTemp -= 1
                temp = datetime.strptime(day,"%Y-%m-%d").date()
                if ((temp - todayVar).days) >= daysRemaining:
                    break
                for slot in calendar[day]:
                    if timeTemp <= 0:
                        break
                    if slot["type"] == "P" and slot["task"]=="":
                        slot["task"] = task["TaskName"]
                        slot["TaskID"] = task["TaskID"]
                        timeTemp = timeTemp - slot["Duration"]

                if timeTemp > 0:
                    for slot in calendar[day]:
                        if timeTemp <= 0:
                            break
                        if slot["type"] == "A" and slot["task"]=="":
                            slot["task"] = task["TaskName"]
                            slot["TaskID"] = task["TaskID"]
                            timeTemp = timeTemp - slot["Duration"]

                if timeTemp <= 0:
                    timeTemp = timePerDay
                    totalTime -= timePerDay
                else:
                    totalTime = totalTime - (timePerDay - timeTemp)
                    timePerDay = int((totalTime)/daysTemp)
                    timeTemp = timePerDay

        elif task["Priority"]=="early":
            days = (db.execute("SELECT EorLDays FROM UserInfo WHERE UserID = :userid;", userid=session["user_id"]))[0]["EorLDays"]
            daysConst = days
            timePerDay = int(totalTime/days)
            timeTemp = timePerDay
            for day in calendar:
                temp = datetime.strptime(day,"%Y-%m-%d").date()
                if ((temp - todayVar).days) >= daysConst:
                    break
                for slot in calendar[day]:
                    if timeTemp <= 0:
                        break
                    if slot["type"] == "P" and slot["task"]=="":
                        slot["task"] = task["TaskName"]
                        slot["TaskID"] = task["TaskID"]
                        timeTemp = timeTemp - slot["Duration"]
                if timeTemp > 0:
                    for slot in calendar[day]:
                        if timeTemp<=0:
                            break
                        if slot["type"] == "A" and slot["task"]=="":
                            slot["task"] = task["TaskName"]
                            slot["TaskID"] = task["TaskID"]
                            timeTemp = timeTemp - slot["Duration"]
                days -= 1

                if timeTemp <= 0:
                    timeTemp = timePerDay
                    totalTime -= timePerDay
                else:
                    totalTime = totalTime - (timePerDay - timeTemp)
                    timePerDay = int((totalTime)/days)
                    timeTemp = timePerDay

        elif task["Priority"]=="late":
            days = (db.execute("SELECT EorLDays FROM UserInfo WHERE UserID = :userid;", userid=session["user_id"]))[0]["EorLDays"]
            timePerDay = int(totalTime/days)
            timeTemp = timePerDay
            daysTemp = daysRemaining
            for day in calendar:

                daysTemp-=1
                if daysTemp>=days:
                    continue
                else:
                    temp = datetime.strptime(day,"%Y-%m-%d").date()
                    if ((temp - todayVar).days) >= daysRemaining:
                        break
                    for slot in calendar[day]:
                        if timeTemp <= 0:
                            break
                        if slot["type"] == "P" and slot["task"]=="":
                            slot["task"] = task["TaskName"]
                            slot["TaskID"] = task["TaskID"]
                            timeTemp = timeTemp - slot["Duration"]
                    if timeTemp > 0:
                        for slot in calendar[day]:
                            if timeTemp<=0:
                                break
                            if slot["type"] == "A" and slot["task"]=="":
                                slot["task"] = task["TaskName"]
                                slot["TaskID"] = task["TaskID"]
                                timeTemp = timeTemp - slot["Duration"]
                    days -= 1
                    if days <=0:
                        break
                    if timeTemp <= 0:
                        timeTemp = timePerDay
                        totalTime -= timePerDay
                    else:
                        totalTime = totalTime - (timePerDay - timeTemp)
                        timePerDay = int((totalTime)/days)
                        timeTemp = timePerDay



    #printCalendar(calendar)

    for day in calendar:
        for slot in calendar[day]:
            if slot["task"]!="":
                db.execute("INSERT INTO Slot (SlotID, TaskID, Date, StartTime, EndTime, Duration) VALUES (NULL, :taskid, :date, :starttime, :endtime, :duration);", taskid=slot["TaskID"], date=day, starttime=slot["StartTime"], endtime=slot["EndTime"], duration=slot["Duration"])




    return redirect("/timetableDisplay")


########
def OutdatedTasks():
    tasks = db.execute("SELECT * FROM Tasks WHERE UserID = :userid", userid=session["user_id"])
    today = date.today()
    taskDic={}
    for task in tasks:
        taskDic[task["TaskID"]] = task["Deadline"]
    delete=[]
    for key in taskDic:
        if (datetime.strptime(taskDic[key],"%Y-%m-%d").date())>today:
            delete.append(key)
    for i in delete:
        del taskDic[i]
    for key in taskDic:
        duration = db.execute("SELECT DurationOfTask FROM Tasks WHERE TaskID = :key;", key=key)[0]["DurationOfTask"]
        CurrentTime = db.execute("SELECT CurrentTime FROM UserInfo WHERE UserID = :userid", userid=session["user_id"])[0]["CurrentTime"]
        CurrentTime += int(duration)
        db.execute("UPDATE UserInfo SET CurrentTime = :CurrentTime WHERE UserID = :userid", CurrentTime=CurrentTime, userid=session["user_id"])
        db.execute("DELETE FROM Tasks WHERE TaskID = :key;", key=key)
#this function deletes all the tasks that are before the current date
#before deleting the task it also adds its duration to the amount of minutes the user has worked for (CurrentTime)
######
def achievement(CurrentTime):
    if 0<= CurrentTime<10:
        return ["Stone","#888c8d"]
    elif 10<=CurrentTime<25:
        return ["Bronze","#cd7f32"]
    elif 25<=CurrentTime<50:
        return ["Silver","#C0C0C0"]
    elif 50<=CurrentTime<100:
        return ["Emerald","#50c878"]
    elif 100<=CurrentTime<150:
        return ["Gold","#ffd700"]
    elif 150<=CurrentTime<200:
        return ["Platinum","#e5e4e2"]
    elif 200<=CurrentTime:
        return ["Diamond","#b9f2ff"]
#This function takes in the number of hours the user has worked as a parameter and returns the users level and the colour associated with that level



def printCalendar(calendar):
    for day in calendar:
        print(day)
        print(calendar[day])
        print("\n")



# @app.route("/timetable",methods=['POST','GET'])
# @login_required
# def timetableDisplay():
#     duration  = db.execute("SELECT DurationOfBlocks FROM UserInfo WHERE UserID=:userid;",userid=session["user_id"])
#     slots = db.execute("SELECT * FROM Slot WHERE UserID =:userid;", userid=session["user_id"])
#     today = date.today()
#     weekday = weekdays2[today.weekday()]
#     rows=[]
#     sleepSchedule = db.execute("SELECT * FROM DayTimes WHERE UserID=:userid;",userid=session["user_id"])
#     for item in sleepSchedule:
#         if item["Day"] == weekdays[i]:
#             wakeup= item["WakeUp"]
#             sleep = item["Sleep"]
#             sleep = datetime.combine(date.today(), time(int(sleep[:2]), int(sleep[3:])))
#             dt = datetime.combine(date.today(), time(int(wakeup[:2]), int(wakeup[3:])))
#             rows.append([dt.strftime("%H:%M")])
#             while dt < sleep:
#                 dt += timedelta(minutes=duration)
#                 i.append([dt.strftime("%H:%M")])
#
#
#
#
#
#
#     return render_template("timetable.html", weekdays=weekdays, )

#######
@app.route("/timetableDisplay",methods=['GET'])
@login_required
def timetablePreview():
    slots = db.execute("SELECT Date, StartTime, EndTime, SubjectID, TaskName FROM Slot, Tasks WHERE Slot.TaskID = Tasks.TaskID AND Tasks.UserID = :userid;", userid=session["user_id"])
    #selects the slots from the database for the user that need to be displayed on the timetable
    today = date.today()
    timetable = {}
    maxArr = []
    if slots == []:
        flash('You currently have no tasks. Please add some.')
        return redirect(url_for("tasks"))
    #if there are no slots user is redirected to tasks page with an error message
    for slot in slots:
        maxArr.append(datetime.strptime(slot["Date"],"%Y-%m-%d").date())
    maxDate = max(maxArr)
    #converting all dates into datetime formats and storing them in maxarr so that the maximum date can be found using the max function
    dif = (maxDate - today).days
    for i in range(dif+1):
        timetable[(today+timedelta(days=i)).strftime('%A, %e %B')]=[]
    #adding key,value pairs to the timetable dictionary with the key as each of the days till the maximum date and a value as an array
    for slot in slots:
        dateVar = datetime.strptime(slot["Date"],"%Y-%m-%d").date()
        if dateVar < today:
            continue
        else:
            (timetable[dateVar.strftime('%A, %e %B')]).append(slot)
    #appending all the slots into the array for the day in the timetable dictionary that they are scheduled for
    colours = {}
    timetableNew = {}
    for key in timetable:
        timetableNew[key] = {}
    #creating a new timetable dictionary with all the same keys as the previous one but with a dictionary as each of its values
    for key in timetable:
        for i in timetable[key]:
            subject = (db.execute("SELECT SubjectName, Colour FROM Subjects WHERE SubjectID= :subjectid;", subjectid= i["SubjectID"]))
            (timetableNew[key])[i["TaskName"]+" ("+subject[0]["SubjectName"]+")"] = i["StartTime"] + " - " + i["EndTime"]
            colours[i["TaskName"]+" ("+subject[0]["SubjectName"]+")"] = subject[0]["Colour"]
    #in each of the dictionaries each of the task name's and subjects corresponding to each slot for that day are set as values and the start time and end time of the slot is assigned as the value
    #this happens for every day in the dictionary
    #a colours dictionary is also created to store the colours for each slot in each day

    CurrentTime = db.execute("SELECT CurrentTime FROM UserInfo WHERE UserID=:userid", userid=session["user_id"])[0]["CurrentTime"]
    CurrentHours= CurrentTime/60
    level = achievement(CurrentHours)
    levelColour = level[1]
    level = level[0]
    #these few lines acquires the number of minutes the user has worked and assigns a level to it using the achivement function
    return render_template("timetable.html", timetable=timetableNew, colours =colours, CurrentTime=CurrentTime, level=level, levelColour=levelColour)
    #these dictionaries are then sent to the html page along with the variables to display the users level and number of hours



@app.route("/EditTasks",methods=['POST','GET'])
@login_required
def EditTasks():
    return render_template("EditTask.html")

@app.route("/EditSubjects",methods=['POST','GET'])
@login_required
def EditSubjects():
    return render_template("EditSubjects.html")


@app.route("/DeleteSubjects",methods=['POST','GET'])
@login_required
def DeleteSubjects():
    if request.method == "POST":
        subject = request.form.get("subject")
        db.execute("DELETE FROM Subjects WHERE SubjectID= :subjectid", subjectid= subject)
        tasks = db.execute("SELECT TaskID FROM Tasks WHERE SubjectID= :subjectid", subjectid= subject)
        db.execute("DELETE FROM Tasks WHERE SubjectID= :subjectid", subjectid= subject)
        for i in tasks:
            db.execute("DELETE FROM Slot WHERE TaskID= :taskid", taskid= i["TaskID"])
        #deletes subject, deletes tasks associated with that subject and then deletes slots associated with that task
        return redirect("/timetableDisplay")
        #redirects user back to the timetable

    else:
        subjectDic = db.execute("SELECT SubjectID, SubjectName FROM Subjects WHERE UserID =:userid", userid= session["user_id"])
        subjects={}
        for i in subjectDic:
            subjects[i["SubjectID"]] = i["SubjectName"]
        return render_template("DeleteSubjects.html", subjects=subjects)
#creates a dictionary with all the subjectID's as the keys and their corresponding subject names as the values
#this is then sent ot the html page so that when the user selects a subject the subjectid is posted back to the application

@app.route("/DeleteTasks",methods=['POST','GET'])
@login_required
def DeleteTasks():
    if request.method == "POST":
        task = request.form.get("task")
        db.execute("DELETE FROM Tasks WHERE TaskID= :taskid", taskid= task)
        db.execute("DELETE FROM Slot WHERE TaskID= :taskid", taskid= task)
        return redirect("/timetableDisplay")
        #deletes the task selected and the slots associated with it and then redirects the user back to the timetable

    else:
        tasksDic = db.execute("SELECT TaskID, TaskName, SubjectID FROM Tasks WHERE UserID =:userid", userid= session["user_id"])
        tasks={}
        for i in tasksDic:
            subject = (db.execute("SELECT SubjectName FROM Subjects WHERE SubjectID= :subjectid", subjectid=i["SubjectID"]))[0]["SubjectName"]
            tasks[i["TaskID"]] = i["TaskName"]+" ("+subject+")"
        return render_template("DeleteTasks.html", tasks=tasks)
#creates a dictionary with all the taskID's as the keys and their corresponding task names as the values
#this is then sent ot the html page so that when the user selects a task the task is posted back ot the application

@app.route("/logout")
def logout():

    # clears the session - forgets any user_id's
    session.clear()

    # Redirect user to login form
    return redirect("/login")
