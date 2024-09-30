from py_spring_redis.redis_client import RedisClient, RedisProperties
from py_spring_redis.redis_crud_repository import RedisCrudRepository, RedisKeyDocument
from loguru import logger
from py_spring import Component, EntityProvider


# Define a Redis document model for a BankAccount
class BankAccountDocument(RedisKeyDocument):
    """A document that represents a bank account stored in Redis."""
    account_holder: str
    balance: float


# Repository for handling CRUD operations on BankAccountDocument
class BankAccountRedisRepository(RedisCrudRepository[BankAccountDocument]):
    """A repository for managing bank accounts in Redis."""
    ...

# Service that performs business logic related to bank accounts
class BankService(Component):
    """Service to manage bank accounts stored in Redis."""
    
    # Inject the repository for handling bank accounts
    repo: BankAccountRedisRepository

    def post_construct(self) -> None:
        """Initialize and perform operations once the component is constructed."""
        # Create a new bank account document
        new_account = BankAccountDocument(
            id="acc_001",
            account_holder="John Smith",
            balance=1000.00  # Initial balance
        )

        # Save the new account to Redis
        self.repo.save(new_account)
        logger.info(f"New account created: {new_account.account_holder}, Balance: {new_account.balance}")

        # Deposit money into the account
        self.deposit("acc_001", 500.00)

        # Check the balance
        current_balance = self.get_balance("acc_001")
        logger.info(f"Current balance for John Smith: {current_balance}")

    def deposit(self, account_id: str, amount: float) -> None:
        """Deposits money into the specified bank account."""
        account = self.repo.find_by_id(account_id)
        if not account:
            logger.error(f"Account {account_id} not found!")
            return

        account.balance += amount
        self.repo.save(account)
        logger.info(f"Deposited {amount} into account {account_id}. New balance: {account.balance}")

    def get_balance(self, account_id: str) -> float:
        """Retrieves the current balance of the specified bank account."""
        account = self.repo.find_by_id(account_id)
        if not account:
            logger.error(f"Account {account_id} not found!")
            return 0.0

        return account.balance

    def withdraw(self, account_id: str, amount: float) -> None:
        """Withdraws money from the specified bank account, ensuring sufficient balance."""
        account = self.repo.find_by_id(account_id)
        if not account:
            logger.error(f"Account {account_id} not found!")
            return

        if account.balance < amount:
            logger.error(f"Insufficient balance in account {account_id}!")
            return

        account.balance -= amount
        self.repo.save(account)
        logger.info(f"Withdrew {amount} from account {account_id}. New balance: {account.balance}")


def provide_redis_test_context() -> EntityProvider:
    """Provides the entity provider with Redis components for testing."""
    provider = EntityProvider(
        properties_classes= [RedisProperties],
        component_classes=[BankService, BankAccountRedisRepository],
        depends_on= [
            RedisCrudRepository,
            RedisClient
        ]
    )
    return provider