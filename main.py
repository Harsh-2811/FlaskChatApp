from flask import Flask,render_template,request,url_for,redirect,flash
from flask_login import LoginManager,current_user,login_user,logout_user,login_required
from db import *
from flask_socketio import SocketIO, join_room, leave_room
import json
app=Flask(__name__)
socketio=SocketIO(app)
app.secret_key="Harsh2811"
login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_message="Please Login First To Access Website"
login_manager.login_view = 'login'
@app.route("/")
@login_required
def home():
    rooms = []
    users=[]
    if current_user.is_authenticated():
        rooms = get_rooms_for_user(current_user.username)
        users=get_all_user()
    return render_template("index.html", rooms=rooms,users=users)

@app.route('/create-room',methods=['GET','POST'])
@login_required
def create_room():
    if request.method == 'POST':
        room_name = request.form.get('room_name')
        usernames = [username.strip() for username in request.form.get('members').split(',')]

        if len(room_name) and len(usernames):
            room_id = save_room(room_name, current_user.username)
            if current_user.username in usernames:
                usernames.remove(current_user.username)
            add_room_members(room_id, room_name, usernames, current_user.username)
            return redirect(url_for('view_room', room_id=room_id))
        else:
           flash("Failed to create room")
    return render_template("create_room.html")
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        password_input = request.form.get('password')
        user = get_user(username)
        print(user)
        if user and user.check_password(password_input):
            login_user(user)
            return redirect(url_for('home'))
        else:
            message = 'Failed to login!'
    return render_template('login.html', message=message)

@app.route('/register', methods=['GET', 'POST'])
def register():
    message=''
    if request.method == "POST":
        username = request.form.get('username')
        password_input = request.form.get('password')
        email=request.form.get('email')
        user = get_user(username)
        if user :
            message="Already a Member"
            return render_template("register.html",message=message)

        save_user(username,email,password_input)

        flash("you are successfuly Registered in")
        return redirect(url_for('login'))

    return render_template("register.html")
@app.route('/rooms/<room_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_room(room_id):
    room = get_room(room_id)
    if room and is_room_admin(room_id,current_user.username):
        exisiting_room_members= [member['_id']['username'] for member in get_room_members(room_id)]

        room_members_str=",".join(exisiting_room_members)
        if request.method == 'POST':
            room_name = request.form.get('room_name')
            room['name'] = room_name
            update_room(room_id, room_name)

            new_members = [username.strip() for username in request.form.get('members').split(',')]
            members_to_add = list(set(new_members) - set(exisiting_room_members))

            members_to_remove = list(set(exisiting_room_members) - set(new_members))
            if len(members_to_add):
                add_room_members(room_id, room_name, members_to_add, current_user.username)
            if len(members_to_remove):
                remove_room_members(room_id, members_to_remove)
            flash('Room edited successfully')
            room_members_str = ",".join(new_members)
        return render_template("edit_room.html",room=room,room_members=room_members_str)
    else:
        return "No Such Romm", 404
@socketio.on("join_room")
def handle_join_room_event(data):
    join_room(data["room"])

    socketio.emit("join_room_announcement",data)


@socketio.on("send_message")
def send_msg(data):
    data['created_at'] = datetime.now().strftime("%d %b, %H:%M")
    save_message(data['room'], data['message'], data['username'])
    socketio.emit("receive_msg", data,room=data["room"])

@app.route('/rooms/<room_id>/messages/')
@login_required
def get_older_messages(room_id):
    room = get_room(room_id)
    if room and is_room_member(room_id, current_user.username):
        page = int(request.args.get('page', 0))
        messages = get_messages(room_id, page)
        print("Hello")
        print(messages)
        return json.dumps(messages)
    else:
        return "Room not found", 404

@app.route("/rooms/<room_id>",methods = ['GET', 'POST'])
@login_required

def view_room(room_id):
    username=current_user.username
    room= get_room(room_id)

    if room and is_room_member(room_id, current_user.username):
        room_members= get_room_members(room_id)
        messages = get_messages(room_id)
        return render_template("chat.html",uname=username,room=room,room_memebrs=room_members,messages=messages)
    else:
        return redirect(url_for("home"))

@socketio.on('leave_room')
def handle_leave_room_event(data):

    leave_room(data['room'])
    socketio.emit('leave_room_announcement', data, room=data['room'])

@login_manager.user_loader
def load_user(username):
    return get_user(username)
@app.route("/logout/")
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))


if __name__ == "__main__":
    socketio.run(app,debug=True)
