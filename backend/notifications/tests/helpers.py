from users.models import User


def make_user(email, phone, role='customer'):
    return User.objects.create(
        first_name='Notif', last_name=role.capitalize(), email=email, phone=phone, neighborhood='Centro', city='Manaus',
        state='AM', address='Rua A', postal_code='69000000', role=role,
    )
