from src.domain.value_objects.money import Money
from src.domain.value_objects.ids.product_id import ProductId
from src.domain.value_objects.ids.vending_machine_id import VMId
from src.domain.value_objects.command_result import CommandResult


def test_money_from_rubles():
    money = Money(rubles=10.50)
    assert money.as_ruble() == 10.50


def test_money_from_kopecks():
    money = Money(kopecks=1050)
    assert money.as_ruble() == 10.50


def test_command_result_fields():
    result = CommandResult(success=False, step="send_command", message="timeout", attempts=3)
    assert result.success is False
    assert result.attempts == 3


def test_product_id_value():
    assert ProductId(42).value == 42


def test_vm_id_value():
    assert VMId(101).value == 101
