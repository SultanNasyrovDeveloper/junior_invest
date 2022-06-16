from fileinput import filename
import sqlite3
import os
from datetime import datetime, timedelta
from unicodedata import name
from flask import Flask, render_template, request, g, abort,  redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from FDataBase import FDataBase
from UserLogin import UserLogin

# Конфигурация
DATABASE = "JI.db"
SECRET_KEY = "QCQWCwfqw23r*7237^^23n2o3fqwc32"
MAX_CONNECT_LENGTH = 1536 * 1536 # 3мб максимальный объем фотокарточки
UPLOAD_FOLDER = '/static/uploads/project'
ALLOWED_EXTENSIONS = ['pdf', 'pptx']

app = Flask(__name__)
app.config.from_object(__name__)
app.config['UPLOAD_FOLDER'] = app.root_path + UPLOAD_FOLDER
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Упс... 😖 \nАвторизуйся для того, чтобы пользоваться данной страницей'
login_manager.login_message_category = "danger"

app.config.update(dict(DATABASE=os.path.join(app.root_path, "JI.db")))

dbase = None
@app.before_request
def before_request():
    global dbase
    db = get_db()
    dbase = FDataBase(db)

@login_manager.user_loader
def load_user(user_id):
    return UserLogin().fromDB(user_id, dbase)

# Админ панель
@app.route('/admin_panel/main')
@app.route('/admin_panel')
def admin_panel():
    return render_template('admin.html', feedback=dbase.getFeedback(), title="Панель управления сайтом")

@app.route('/admin_panel/feedback')
def admin_feedback():
    return render_template('adminFeedback.html', feedback=dbase.getFeedback(), title="Панель управления сайтом")


# Основная ветка сайта
@app.route('/')
@app.route('/main_page', methods=['POST', 'GET'])
def main_page():
    if request.method == "POST":
        res = dbase.addMessage(first_name=request.form['firstName'], last_name=request.form['lastName'],
                               telephone_number=request.form['number'], email_address=request.form['email'],
                               address=request.form['address'], subject=request.form['subject'],
                               message=request.form['message'])
        if not res:
            flash("Сообщение не отправлено", category="danger")
        else:
            flash("Сообщение отправлено", category="success")
    return render_template("main_page.html", title="Главное меню")


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта ✔", category="success")
    return redirect((url_for('login')))


def allowed_file(filename):
    """Функция проверки файла"""
    if "." in filename:
        list_name = filename.split(".")
        if list_name[-1] in ALLOWED_EXTENSIONS: return True
        else: return False

@app.route('/creat_project', methods=['POST', 'GET'])
@login_required
def create_project():
    return render_template('createProject.html', title="Создание проекта")


@app.route('/upload_project', methods=['POST', 'GET'])
@login_required
def upload_project():
    if request.method == "POST":
        if len(request.form['NameProject']) > 0:
            if len(request.form['CategoryProject']) > 0:
                if len(request.form['message']) > 0:
                    if 'file' not in request.files:
                        flash('Упс... 😖 Я не могу прочитать файл"', category='danger')
                    else:
                        file = request.files['file']
                        if file.filename != '':
                            if file and allowed_file(file.filename):
                                new_filename = f"({datetime.now().hour}h-" \
                                               f"{datetime.now().minute}m-" \
                                               f"{datetime.now().second}s) " + str(file.filename)
                                file.save(os.path.join(app.config['UPLOAD_FOLDER'], new_filename))
                                user_info = dbase.getUserInfo(current_user.get_id())
                                res = dbase.addProject(name_project=request.form['NameProject'],
                                                       category_project=request.form['CategoryProject'],
                                                       description_project=request.form['message'],
                                                       name_file_project=new_filename,
                                                       author_user_id=current_user.get_id(),
                                                       author_first_name=user_info['FIRST_NAME'],
                                                       author_last_name=user_info['LAST_NAME'],
                                                       author_username=user_info['USER_NAME'],
                                                       date_of_creation = f"{datetime.now().hour}:"
                                                                          f"{datetime.now().minute}:"
                                                                          f"{datetime.now().second}"
                                                       )
                                if not res:
                                    flash('Упс... 😖 Ошибка создания проект', category='danger')
                                else:
                                    flash('Проект успешно создан ✔', category="success")
                                return redirect(url_for('view_projects'))
                        else:
                            flash('Упс... 😖 Вы не прикрепили файл', category='danger')
                else:
                    flash('Упс... 😖 Вы не описали проект', category='danger')
            else:
                flash('Упс... 😖 Вы не написали категорию проекта', category='danger')
        else:
            flash('Упс... 😖 Вы не написали название проекта', category='danger')
    return render_template('createProject.html', title='Создание проекта')


@app.route('/view_projects')
def view_projects():
    return render_template('view_projects.html', title='Проекты', project=dbase.getProjects())


@app.route('/view_projects/download_id_project=<int:id_post>', methods=['POST', 'GET'])
def downloadProject(id_post):
    infoProject = dbase.getProject(id_post)
    if not infoProject:
        abort(404)
    file_l_project = infoProject['NAME_FILE_PROJECT'].split('.')
    if file_l_project[-1] == "pptx":
        return send_file(path_or_file=f"{app.config['UPLOAD_FOLDER']}/{infoProject['NAME_FILE_PROJECT']}",
                         as_attachment=False, download_name=f"{infoProject['NAME_PROJECT']}.pptx" )
    elif file_l_project[-1] == "pdf":
        return send_file(path_or_file=f"{app.config['UPLOAD_FOLDER']}/{infoProject['NAME_FILE_PROJECT']}",
                         as_attachment=False, download_name=f"{infoProject['NAME_PROJECT']}.pdf")
    else:
        abort(404)


@app.route('/view_projects/id_project=<int:id_post>')
def showProject(id_post):
    infoProject = dbase.getProject(id_post)
    if not infoProject:
        abort(404)

    return render_template('projectV.html', title=infoProject['NAME_PROJECT'], project=infoProject)


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title=f'Профиль', us=dbase.getUserInfo(current_user.get_id()))


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    if request.method == 'POST':
        user = dbase.getUserByEmail(request.form['email'])
        if user and check_password_hash(user['PASSWORD'], request.form['psw']):
            userlogin = UserLogin().create(user)
            rememberMe = True if request.form.get('checkbox') else False
            login_user(userlogin, remember=rememberMe)
            return redirect(request.args.get('next') or url_for('profile'))

        flash('Неверный логин или пароль',category="danger")
    return render_template('login.html', title="Авторизация")


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == "POST":
        if len(request.form['psw']) >= 8:
            if request.form['psw'] == request.form['psw2']:
                    hash = generate_password_hash(request.form['psw'])
                    res = dbase.addUser(first_name=request.form['firstName'], last_name=request.form['lastName'],
                                        username=request.form['username'], telephone_number=request.form['number'],
                                        email_address=request.form['email'], password=hash)
                    if not res:
                        flash("Ошибка регистрации", category="danger")
                    else:
                        return redirect(url_for('login'))
            else:
                flash("Пароли должны совпадать", category="danger")
        else:
            flash("Пароль должен быть больше 8 символов", category="danger")
    return render_template('register.html', title="Регистрация")


@app.route('/rules')
def rules_page():
    return render_template('rules.html', title="Правила платформы")


@app.route('/coins')
def coins():
    return render_template("coins.html", title="JuniorCoin")


@app.errorhandler(404)
def error_404(error):
    return render_template('error404.html', title="Ошибка")


def connect_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def get_db():
    if not hasattr(g, 'link_db'):
        g.link_db = connect_db()
    return g.link_db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'link_db'):
        g.link_db.close()

def create_db():
    db = connect_db()
    with app.open_resource('ji_db.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()
    db.close()


if __name__ == '__main__':
    app.run()
