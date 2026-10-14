import getpass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from agencies.models import Agency

User = get_user_model()


class Command(BaseCommand):
    help = 'Create member agent and admin user with passwords'

    def add_arguments(self, parser):
        parser.add_argument(
            '--admin-username',
            type=str,
            default='admin',
            help='Username for admin/developer user (default: admin)'
        )
        parser.add_argument(
            '--admin-password',
            type=str,
            help='Password for admin/developer user (will prompt if not provided)'
        )
        parser.add_argument(
            '--admin-email',
            type=str,
            default='admin@nahdtravels.com',
            help='Email for admin/developer user (default: admin@nahdtravels.com)'
        )
        parser.add_argument(
            '--agent-username',
            type=str,
            default='agent',
            help='Username for agent user (default: agent)'
        )
        parser.add_argument(
            '--agent-password',
            type=str,
            help='Password for agent user (will prompt if not provided)'
        )
        parser.add_argument(
            '--agent-email',
            type=str,
            default='agent@nahdtravels.com',
            help='Email for agent user (default: agent@nahdtravels.com)'
        )
        parser.add_argument(
            '--agency-id',
            type=int,
            help='Agency ID for the agent user (will use first agency if not provided)'
        )
        parser.add_argument(
            '--member-username',
            type=str,
            default='member',
            help='Username for member user (default: member)'
        )
        parser.add_argument(
            '--member-password',
            type=str,
            help='Password for member user (will prompt if not provided)'
        )
        parser.add_argument(
            '--member-email',
            type=str,
            default='member@nahdtravels.com',
            help='Email for member user (default: member@nahdtravels.com)'
        )
        parser.add_argument(
            '--reset-admin-password',
            action='store_true',
            help='Reset password for existing admin user'
        )

    def handle(self, *args, **options):
        # Create admin/developer user
        admin_username = options['admin_username']
        admin_password = options['admin_password']
        admin_email = options['admin_email']

        if not admin_password:
            admin_password = getpass.getpass(f'Enter password for admin user ({admin_username}): ')

        # Check if admin user already exists
        admin_user = User.objects.filter(username=admin_username).first()
        if admin_user:
            if options['reset_admin_password']:
                admin_user.set_password(admin_password)
                admin_user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully reset password for admin user: {admin_username}')
                )
                self.stdout.write(f'  Email: {admin_user.email}')
                self.stdout.write(f'  New Password: {admin_password}')
                self.stdout.write(f'  Role: {admin_user.role}')
                self.stdout.write(f'  Is Staff: {admin_user.is_staff}')
                self.stdout.write(f'  Is Superuser: {admin_user.is_superuser}')
            else:
                self.stdout.write(
                    self.style.WARNING(f'Admin user "{admin_username}" already exists. Use --reset-admin-password to reset password.')
                )
        else:
            admin_user = User.objects.create_user(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                role='member',
                is_staff=True,
                is_superuser=True,
                is_active=True,
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created admin user: {admin_username}')
            )
            self.stdout.write(f'  Email: {admin_email}')
            self.stdout.write(f'  Password: {admin_password}')
            self.stdout.write('  Role: member (superuser - manage via Django admin)')
            self.stdout.write('  Is Staff: True')
            self.stdout.write('  Is Superuser: True')

        # Create agent user
        agent_username = options['agent_username']
        agent_password = options['agent_password']
        agent_email = options['agent_email']
        agency_id = options['agency_id']

        if not agent_password:
            agent_password = getpass.getpass(f'Enter password for agent user ({agent_username}): ')

        # Get or create agency
        agency = None
        if agency_id:
            try:
                agency = Agency.objects.get(id=agency_id)
            except Agency.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Agency with ID {agency_id} does not exist.')
                )
                return
        else:
            # Try to get first active agency
            agency = Agency.objects.filter(is_active=True).first()
            if not agency:
                # Create a default agency
                self.stdout.write(
                    self.style.WARNING('No agency found. Creating default agency...')
                )
                agency = Agency.objects.create(
                    name='Default Agency',
                    code='DEFAULT001',
                    email='default@nahdtravels.com',
                    phone='+1234567890',
                    address='123 Main Street',
                    city='Default City',
                    state='Default State',
                    country='Default Country',
                    postal_code='12345',
                    is_active=True
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created default agency: {agency.name} (ID: {agency.id})')
                )

        # Check if agent user already exists
        if User.objects.filter(username=agent_username).exists():
            self.stdout.write(
                self.style.WARNING(f'Agent user "{agent_username}" already exists. Skipping...')
            )
        else:
            User.objects.create_user(
                username=agent_username,
                email=agent_email,
                password=agent_password,
                role='agent',
                agency=agency,
                is_active=True,
                first_name='Agent',
                last_name='User'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created agent user: {agent_username}')
            )
            self.stdout.write(f'  Email: {agent_email}')
            self.stdout.write(f'  Password: {agent_password}')
            self.stdout.write('  Role: agent')
            self.stdout.write(f'  Agency: {agency.name} (ID: {agency.id})')

        # Create member user
        member_username = options['member_username']
        member_password = options['member_password']
        member_email = options['member_email']

        if not member_password:
            member_password = getpass.getpass(f'Enter password for member user ({member_username}): ')

        # Use same agency as agent or get first active agency
        if not agency:
            agency = Agency.objects.filter(is_active=True).first()
            if not agency:
                # Create a default agency
                self.stdout.write(
                    self.style.WARNING('No agency found. Creating default agency...')
                )
                agency = Agency.objects.create(
                    name='Default Agency',
                    code='DEFAULT001',
                    email='default@nahdtravels.com',
                    phone='+1234567890',
                    address='123 Main Street',
                    city='Default City',
                    state='Default State',
                    country='Default Country',
                    postal_code='12345',
                    is_active=True
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created default agency: {agency.name} (ID: {agency.id})')
                )

        # Check if member user already exists
        if User.objects.filter(username=member_username).exists():
            self.stdout.write(
                self.style.WARNING(f'Member user "{member_username}" already exists. Skipping...')
            )
        else:
            User.objects.create_user(
                username=member_username,
                email=member_email,
                password=member_password,
                role='member',
                agency=agency,
                is_active=True,
                first_name='Member',
                last_name='User'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created member user: {member_username}')
            )
            self.stdout.write(f'  Email: {member_email}')
            self.stdout.write(f'  Password: {member_password}')
            self.stdout.write('  Role: member')
            self.stdout.write(f'  Agency: {agency.name} (ID: {agency.id})')

        self.stdout.write(
            self.style.SUCCESS('\n✓ User creation completed!')
        )

