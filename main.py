#------------------------------------------------------------------------------------------
#                   Подключение библиотек и настройка конфигурации
#------------------------------------------------------------------------------------------
import sqlite3

from flask import Flask, render_template, request, flash, redirect, url_for, make_response
from sqlalchemy import BLOB
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager,login_user,login_required, current_user, logout_user
from UserLogin import UserLogin
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from matplotlib.dates import DateFormatter
from matplotlib.figure import Figure
import matplotlib as mpl
import matplotlib.pyplot as plt

# Для работы с БД
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '2b1e657f5ce6ffbf5b2426d173440d3658491779' # Для работы сессий
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 # Максимальный размер в байтах файла, который можно загрузить в БД
db = SQLAlchemy(app)

# Для работы аутентификации
login_manager = LoginManager(app)
login_manager.login_view = 'login' # что показывать, при попытки зайти на страницы с обязательной авторизацией
login_manager.login_message = "Авторизуйтесь для доступа к закрытым страницам"
login_manager.login_message_category = "alert alert-primary"

@login_manager.user_loader
def load_user(user_id):
    print("load_user")
    return UserLogin().fromDB(user_id,db,User,app)

#------------------------------------------------------------------------------------------
#                   Классы Базы Данных "database.db"
#------------------------------------------------------------------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fio = db.Column(db.String(50), unique=True)
    login = db.Column(db.String(50), nullable=True)
    psw = db.Column(db.String(500), nullable = True)
    avatar = db.Column(BLOB, default = None)

class Thread(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(50))
    Type_of_data = db.Column(db.String(50))
    Value = db.Column(db.Float)
    DateTime = db.Column(db.DateTime(), default= datetime.now)
    Range_Id = db.Column(db.Integer, db.ForeignKey('range.id'))


class Range(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Min = db.Column(db.Float)
    Max = db.Column(db.Float)
    Name = db.Column(db.String(50))
    Type_of_data = db.Column(db.String(50))


class Problem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(50))
    Range_Id = db.Column(db.Integer, db.ForeignKey('range.id'))

class Advice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Content = db.Column(db.String(200))
    Problem_Id = db.Column(db.Integer, db.ForeignKey('problem.id'))



#------------------------------------------------------------------------------------------
#                   Обработчики запросов (страницы сайта)
#------------------------------------------------------------------------------------------

#        Главная страница
#--------------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template('index.html',title = "Главная страница")

#********************************************************АУТЕНТИФИКАЦИЯ*********************************************************************************

#        Страница аутентификации
#--------------------------------------------------------------------------------
@app.route("/login", methods=("POST","GET"))
def login():
    # Если пользователь уже авторизован, перенаправляем на страницу профиля
    if current_user.is_authenticated:
        return redirect(url_for('profile'))

    # Если совершена отправка формы
    if request.method == "POST":
        try:
            user = User.query.filter_by(login = request.form['login']).first() #поиск пол-ля по Логину
            print(user)
            # Если пользователь найден в БД и пароль верный
            if user and check_password_hash(user.psw,request.form['psw']):

                 userlogin = UserLogin().create(user)

                 #Проверка стоит ли галочка "Запомнить меня"
                 rm = True if request.form.get('remainme') else False
                 login_user(userlogin, remember = rm)

                 # Переход туда, куда пытался зайти пользователь/ в профиль
                 return redirect(request.args.get("next") or url_for('profile'))

            flash("Неверная пара логин/пароль","alert-danger")
        except:
            print("Ошибка поиска в базе данных пользователя по логину")
            return False


    return render_template('login.html',title = "Авторизация")


#*******************************************************РЕГИСТРАЦИЯ**********************************************************************************

#        Страница регистрации
#--------------------------------------------------------------------------------
@app.route("/register", methods=("POST","GET"))
def register():
    # Если произошла отправка формы
    if request.method == "POST":

        # Проверка на длину введенных строк
        if len(request.form['fio']) > 4 and len(request.form['login']) > 4 \
                and len(request.form['psw']) > 4 :

            # Проверка на соответствие паролей
            if request.form['psw'] == request.form['psw2']:

                # Проверка на уникальность логина
                if User.query.filter_by(login = request.form['login']).all():
                    flash("Пользователь с таким логином уже существует", "alert-danger")
                else:
                    try:
                        hash = generate_password_hash((request.form['psw']))
                        u = User(fio=request.form['fio'],login=request.form['login'],psw=hash, avatar = None)
                        db.session.add(u)
                        db.session.flush()
                        db.session.commit()

                        #Авторизация пользователя
                        userlogin = UserLogin().create(u)
                        login_user(userlogin)
                        flash("Вы успешно зарегестрированы", "alert-success")
                        return redirect(url_for('profile'))
                    except:
                        db.session.rollback()
                        print("Ошибка добавления в БД")

            else:
                flash("Пароли не совпадают", "alert-danger")
        else:
            flash("Слишком мало символов, минимальная длина = 4 символа", "alert-danger")


    return render_template('register.html',title = "Регистрация")


#*************************************************************ПРОФИЛЬ******************************************************************************

#        Выход из акканута
#--------------------------------------------------------------------------------
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из акаунта", "alert-success")
    return redirect(url_for('login'))

#        Фото профиля
#--------------------------------------------------------------------------------
@app.route('/userava')
@login_required
def userava():
    img = current_user.get_Avatar(app)
    if not img:
        return ""
    h = make_response(img)
    h.headers['Content-Type'] = 'image/png'
    return h

#        Загрузка фото на профиль
#--------------------------------------------------------------------------------
@app.route('/upload', methods=("POST","GET"))
@login_required
def upload():
    if request.method == 'POST':
        file = request.files['file']

        # Проверка успешна ли была загрузка файла и соответствует ли расширение  phg
        if file and current_user.verifyExt(file.filename):
            try:
                img = file.read()

                # Не пустой ли файл фото
                if not img:
                    flash("Не удалось получить фото", "alert-danger")
                else:
                    try:
                        # Преобразовываем данные в бинарный объект и помещаем в БД
                        binary = sqlite3.Binary(img)
                        User.query.filter_by(id = current_user.get_id()).update({'avatar': binary})
                        db.session.commit()
                        flash("Аватар обновлен", "alert-success")
                    except:
                        print("Ошибка обновления фото в БД")

            except FileNotFoundError as e:
                flash("Ошибка чтения файла", "alert-danger")
        else:
            flash("Не тот формат фото, нужен \"png\"", "alert-danger")

    return redirect(url_for('profile'))


#        Профиль
#--------------------------------------------------------------------------------
@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', title="Ваш профиль", fio = current_user.get_fio(), login = current_user.get_login())


#************************************************************************ВСЕ ПРОФИЛИ***************************************************************

#        Профили всех пользователей
#--------------------------------------------------------------------------------
@app.route('/all_profiles')
@login_required
def all_profiles():
    users = User.query.all()
    return render_template('all_profiles.html', title="Профили всех пользователей", users = users)

#        Фото всех профилей
#--------------------------------------------------------------------------------
@app.route('/all_userava/<id>')
@login_required
def all_userava(id):
    user = User.query.filter_by(id=id).first()
    img = user.avatar
    if not img:
        try:
            with app.open_resource(app.root_path + url_for('static', filename='images/default.png'), "rb") as f:
                img = f.read()
        except FileNotFoundError as e:
            print("Не найдено фото профиля по умолчанию: " + str(e))
    if not img:
        return ""
    h = make_response(img)
    h.headers['Content-Type'] = 'image/png'
    return h


#        Добавление пользователя
#--------------------------------------------------------------------------------
@app.route('/add_user', methods=("POST","GET"))
@login_required
def add_user():
    # Если произошла отправка формы
    if request.method == "POST":

        # Проверка на длину введенных строк
        if len(request.form['fio']) > 4 and len(request.form['login']) > 4 \
                and len(request.form['psw']) > 4:

            # Проверка на уникальность логина
            if User.query.filter_by(login=request.form['login']).all():
                flash("Пользователь с таким логином уже существует", "alert-danger")
            else:
                try:
                    hash = generate_password_hash((request.form['psw']))
                    u = User(fio=request.form['fio'], login=request.form['login'], psw=hash, avatar=None)
                    db.session.add(u)
                    db.session.flush()
                    db.session.commit()

                    flash("Пользователь успешно добавлен", "alert-success")
                except:
                    db.session.rollback()
                    print("Ошибка добавления в БД")
        else:
            flash("Слишком мало символов, минимальная длина = 4 символа", "alert-danger")

    return render_template('add_user.html', title="Добавление пользователя")


#        Изменение записи пользователя
#--------------------------------------------------------------------------------
@app.route('/update_user/<id>', methods=("POST","GET"))
@login_required
def update_user(id):
    try:
        user = User.query.filter_by(id=id).first()
    except:
        print("Ошибка чтения записи о пользователе")

    # Если произошла отправка формы
    if request.method == "POST":

        # Проверка на длину введенных строк
        if len(request.form['fio']) > 4 and len(request.form['login']) > 4 \
                and len(request.form['psw']) > 4:

            user_login = User.query.filter_by(login=request.form['login']).first()
            # Проверка на уникальность логина
            if user_login and user_login.login != user.login :
                flash("Пользователь с таким логином уже существует", "alert-danger")
            else:
                try:
                    hash = generate_password_hash((request.form['psw']))

                    user.fio = request.form['fio']
                    user.login = request.form['login']
                    user.psw = hash
                    db.session.commit()

                    flash("Информация о пользователе обновлена успешно", "alert-success")
                except:
                    db.session.rollback()
                    print("Ошибка добавления в БД")
        else:
            flash("Слишком мало символов, минимальная длина = 4 символа", "alert-danger")

    return render_template('update_user.html', id = user.id, title="Изменение данных пользователя", fio=user.fio, login=user.login)


#        Загрузка фото на профиль другого пользователя
#--------------------------------------------------------------------------------
@app.route('/upload_for_user/<id>', methods=("POST","GET"))
@login_required
def upload_for_user(id):
    if request.method == 'POST':
        file = request.files['file']

        # Проверка успешна ли была загрузка файла и соответствует ли расширение  phg
        if file and current_user.verifyExt(file.filename):
            try:
                img = file.read()

                # Не пустой ли файл фото
                if not img:
                    flash("Не удалось получить фото", "alert-danger")
                else:
                    try:
                        # Преобразовываем данные в бинарный объект и помещаем в БД
                        binary = sqlite3.Binary(img)
                        User.query.filter_by(id = id).update({'avatar': binary})
                        db.session.commit()
                        flash("Аватар обновлен", "alert-success")
                    except:
                        db.session.rollback()
                        print("Ошибка обновления фото в БД")

            except FileNotFoundError as e:
                flash("Ошибка чтения файла", "alert-danger")
        else:
            flash("Не тот формат фото, нужен \"png\"", "alert-danger")

    return redirect(url_for('update_user', id=id))


#        Удаление пользователя из списка
#--------------------------------------------------------------------------------
@app.route('/delete_user/<id>')
@login_required
def delete_user(id):

    redirect_f = False
    # Если пользователь удаляет сам себя, то он выходит из системы
    if id == current_user.get_id():
        logout_user()
        redirect_f = True
        flash("Вы удалили свой профиль и вышли из акаунта", "alert-success")

    try:
        User.query.filter_by(id=id).delete()
        db.session.commit()

        # Если пользователь удаляет сам себя, переходим в форму входа
        if(redirect_f == True):
            return redirect(url_for('login'))

        flash("Пользователь успешно удален", "alert-success")

    except:
        db.session.rollback()
        print("Ошибка удаление пользователя в БД")

    users = User.query.all()
    return render_template('all_profiles.html', title="Профили всех пользователей", users=users)



#***************************************************************************************************************************************************

#        Считывание данных с потока и занесение в БД
#--------------------------------------------------------------------------------
@app.route('/get_thread')
def get_thread():
    # Берем данные с сайта
    url = 'http://metadb.ru/flows/18'
    page = requests.get(url)
    soup = BeautifulSoup(page.text, "html.parser")
    content = soup.prettify()
    content.replace("\n", "")
    js = eval(content)
    #print(js['air_temperature']) Для проверки

    try:
        ranges = Range.query.filter_by(Type_of_data='air_temperature').all()
        value = js['air_temperature']
        added = False
        for r in ranges:
            if value >= r.Min and value <= r.Max:
                range_id = r.id
                t = Thread(url=url, Type_of_data='air_temperature', Value=value, Range_Id = range_id)
                db.session.add(t)
                db.session.commit()
                flash("Данные о потоке успешно добавлены", "alert-success")
                added = True
                break

        if added == False:
            print("ОШИБКА ДОБАВЛЕНИЯ ПОТОКА, ЗНАЧЕНИЕ НЕ СООТВЕТСТВУЕТ НИ ОДНОМУ ДИАПАЗОНУ")
            flash("Ошибка добавления потока в БД - НЕ СООТВЕТСТВИЕ НИ ОДНОМУ ИЗ ДИАПАЗОНОВ", "alert-danger")
    except:
        db.session.rollback()
        print("Ошибка добавления записи о потоке")
        flash("Ошибка добавления записи о потоке", "alert-danger")
    return render_template('index.html', title="Главная страница")


#***************************************************************ПОТОКИ******************************************************************************

#        Страница потоков
#--------------------------------------------------------------------------------
@app.route("/thread")
@login_required
def thread():
    # Заполнение массивов x y графика
    #---------------------------------------------------------
    try:
        threads = Thread.query.filter_by(Type_of_data='air_temperature').all()
        x = []
        y = []
        for t in threads:
            x.append(t.DateTime)
            y.append(t.Value)

        # Заполнение значений для зон
        ranges = Range.query.filter_by(Type_of_data='air_temperature').all()
        zones = {}
        names = []
        for r in ranges:
            zones.update({r.Min: r.Max})
            names.append(r.Name)


    except:
        print("Ошибка считывания данных о потоке")

    # Рисование графика
    # ---------------------------------------------------------
    fig = plt.figure(figsize=(16,8))
    plt.scatter(x,y, c = 'black', s = 20, label='Полученное значение')
    plt.grid()

    # Рисование зон температур
    colors = ['#0000FF','#4169E1', '#FFCC99', '#FF6633', 'red']
    i=0
    for zon in zones:
        plt.fill_between(x, zon,
                         zones[zon],
                         alpha=0.2,
                         color = colors[i],
                         linewidth = 3,
                         linestyle='--',
                         label=names[i])
        i+=1

    # Оформление оси времени
    plt.gca().xaxis.set_major_formatter(mpl.dates.DateFormatter('%d_%h-%H:%M')) #Формат
    plt.gca().xaxis.set_major_locator(mpl.dates.AutoDateLocator()) #Шаг

    # Подписи
    plt.title('График значений с датчика "air_temperature"')
    plt.xlabel('Date Time')
    plt.xticks(rotation=30, ha='right')
    plt.ylabel('Value')

    plt.legend() # Запись легенд на график

    # Сохраняем график как изображение и передаем в шаблон
    # ---------------------------------------------------------
    fig.savefig('static/images/air_temperature_plot.png', dpi=fig.dpi)
    return render_template('thread.html',title = "Потоки данных", url = '/static/images/air_temperature_plot.png')


#--------------------------------------------------------------------------------
#        Страница проблем данных с потоков
#--------------------------------------------------------------------------------
@app.route("/thread_problem")
@login_required
def thread_problem():

    #Считывание данных и заполнение строковой переменной для вывода
    try:
        threads = Thread.query.all()

        problem_information =""

        # проходимся по всем потокам и собираем соответствующие им диапазоны и проблемы с решениями
        for t in threads:
            range = Range.query.filter_by(id=t.Range_Id).first()
            problems = Problem.query.filter_by(Range_Id=range.id).all()
            if problems:
                advices = {}
                for p in problems:
                    advices.update({p.Name: (Advice.query.filter_by(Problem_Id=p.id).all())})

                # Формируем строковый вывод
                problem_information += "\n\nДата потока :" + str(t.DateTime)
                problem_information += "\nТип данных :" + str(t.Type_of_data)
                problem_information += "\nПолученное значение :" + str(t.Value)
                for a in advices:
                    problem_information += "\n\tДля данных соответствует проблема : " + a
                    for adv in advices[a]:
                        problem_information += "\n\t\tРешение: " + adv.Content
                problem_information += "\n_____________________________________________________________________________________"
            else:
                print("Со значениям все хорошо, проблем нет")
    except:
        print("Ошибка считывания данных о проблемах в потоках")
    return render_template('thread_problem.html', title="Проблемы на основании данных с потоков", text = problem_information)


#--------------------------------------------------------------------------------
#        Страница диапазонов данных с потоков
#--------------------------------------------------------------------------------
@app.route("/ranges")
@login_required
def ranges():
    try:
        ranges = Range.query.all()
    except:
        print("Ошибка считывания диапазоно из Базы данных")
    return render_template('ranges.html', title="Справочник диапазонов значений", content = ranges)



#--------------------------------------------------------------------------------
#        Страница справочника советов
#--------------------------------------------------------------------------------
@app.route("/advices")
@login_required
def advices():
    try:
        res = db.session.query(
            Advice, Problem, Range,
                ).filter(Advice.Problem_Id == Problem.id,
                    ).filter(Problem.Range_Id == Range.id,
                          ).all()
    except:
        print("Ошибка считывания рекомендаций из Базы данных")

    return render_template('advices.html', title="Справочник рекоммендаций", content = res)



#------------------------------------------------------------------------------------------
#                   Обработчики ошибок
#------------------------------------------------------------------------------------------
@app.errorhandler(404) #страница не найдена
def pageNotFount(error):
    return render_template('page404.html',title= "Страница не найдена")


#------------------------------------------------------------------------------------------
#                   Запуск сервера
#------------------------------------------------------------------------------------------
if __name__ == "__main__":
     app.run(debug=True)