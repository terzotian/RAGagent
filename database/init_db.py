from sqlalchemy import create_engine, text
import os

# 使用项目中配置的连接字符串，连接到 MySQL Server (不指定 DB)
DATABASE_URL = "mysql+mysqlconnector://root:TTZZ3388@localhost:3306"
engine = create_engine(DATABASE_URL)

def execute_sql_file(filename):
    print(f"Executing {filename}...")
    with open(filename, 'r') as f:
        # 读取整个 SQL 文件内容
        sql_content = f.read()

    # 连接数据库
    with engine.connect() as connection:
        # 简单分割 SQL 语句 (注意：这只是一个简单的分割，对于复杂的 SQL 可能不够健壮)
        # 这里 create.sql 主要是建表，分号分割通常没问题
        statements = sql_content.split(';')
        
        for statement in statements:
            if statement.strip():
                try:
                    # 移除注释等
                    print(f"Running statement: {statement[:50]}...")
                    connection.execute(text(statement))
                    connection.commit()
                except Exception as e:
                    print(f"Error executing statement: {e}")

if __name__ == "__main__":
    sql_file = "create.sql"
    if os.path.exists(sql_file):
        execute_sql_file(sql_file)
        print("Database initialized successfully.")
    else:
        print(f"File {sql_file} not found.")
