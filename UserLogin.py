from flask import url_for
from flask_login import UserMixin

#------------------------------------------------------------------------------------------
#                   Класс зарегестрированного пользователя
#------------------------------------------------------------------------------------------
class UserLogin(UserMixin):
    #  Для создания current_user = экземпляр класса UserLogin = запись в user, поиск по id
    # -------------------------------------------------------------------------------------
    def fromDB(self, user_id, db, User, app ):
        try:
            with app.app_context():
                self.__user = User.query.filter_by(id=user_id).first()
            if not self:
                print("Пользователь не найден")
                return False
            return self
        except:
            print("Ошибка получения данных из БД")
            return False

    #  Для нормальной работы Login_Manager
    # -------------------------------------------------------------------------------------
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False
    def create(self,user):
        self.__user = user
        return self

    #  Получение значений полей current_user (полей записи в user таблице)
    # -------------------------------------------------------------------------------------
    def get_id(self):
        return str(self.__user.id)


    def get_fio(self):
        return str(self.__user.fio)


    def get_login(self):
        return str(self.__user.login)


    def get_Avatar(self,app):
        img = None

        # Если фото еще не было загружено, загружаем дефолтное по пути static/images/default.png
        if not self.__user.avatar:
            try:
                with app.open_resource(app.root_path + url_for('static', filename='images/default.png'), "rb") as f:
                    img = f.read()
            except FileNotFoundError as e:
                print("Не найдено фото профиля по умолчанию: " + str(e))
        else:
            img = self.__user.avatar

        return img


    #  Метод проверки загруженного фото на соответствие типу "png"
    # -------------------------------------------------------------------------------------
    def verifyExt(self,filename):
        ext = filename.rsplit('.',1)[1]
        if ext == "png" or ext == "PNG":
            return True
        return False






