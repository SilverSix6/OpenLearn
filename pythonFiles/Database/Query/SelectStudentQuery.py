from DatabaseQuery import DatabaseQuery;
from DatabaseManager import DatabaseManager;

class QuertSelectStudent(DatabaseQuery):
    @classmethod
    def query(cls, dataTuple) -> tuple:
        sql = "SELECT * FROM User WHERE userId = %s"
        
        userId = dataTuple
        if not isinstance(userId, int): #Only allow userId to be an integer
            return None
        
        cursor = DatabaseManager.getDatabaseCursor();
        cursor.execute(sql, (userId))
        studentData = cursor.fetchone()
        
        DatabaseManager.closeConnection()

        return studentData