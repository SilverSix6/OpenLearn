from src.Database.Check.UsernamePasswordCheck import UsernamePasswordCheck
import pytest

def test_UsernamePasswordCheck_valid():
    username = "jsmith"
    password = "jsmith1234"

    validLogin = UsernamePasswordCheck.check((username,password))
    assert(validLogin == True)
    
def test_UsernamePasswordCheck_invalid():
    username = "jsmith"
    password = "wrongpassword"

    validLogin = UsernamePasswordCheck.check((username,password))
    assert(validLogin == False)