import pymysql

connection = pymysql.connect(
    host="localhost",
    port=3306,
    user="root",
    password="",
    database="northwind",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor
)

print("DBAPI connected to Database")

def dbapi_simple_select():
    print("Selecting first 5 item")
    with connection.cursor() as cursor:
        cursor.execute("SELECT ProductID, ProductName FROM products LIMIT 5;")
        rows = cursor.fetchall()
        for row in rows:
            print(row)


def dbapi_parameterized_select():
    print("Selecting with parameter")
    max_price = 20
    with connection.cursor() as cursor:
        sql = "Select ProductName, Unitprice from Products WHERE UnitPrice < %s;"
        cursor.execute(sql, (max_price,))
        rows = cursor.fetchall()
        for row in rows:
            print(row)


def dbapi_insert():
    print("DBAPI Insert")
    with connection.cursor() as cursor:
        sql = "INSERT INTO categories (CategoryName) VALUES (%s);"
        cursor.execute(sql, ("Test Category",))
        connection.commit()
        print("Inserted new category with ID:", cursor.lastrowid)


def dbapi_update():
    print("DBAPI Update")
    with connection.cursor() as cursor:
        sql = "UPDATE products SET UnitPrice = UnitPrice + 1 WHERE ProductID = %s;"
        cursor.execute(sql, (1,))
        connection.commit()
        print("Product 1 price increased.")


def dbapi_transaction_rollback():
    print("\nDBAPI Transaction (with forced rollback):")
    try:
        with connection.cursor() as cursor:
            cursor.execute("UPDATE products SET UnitPrice = -50 WHERE ProductID = 1;")
            raise Exception("Failure!")
    except Exception as e:
        print("Error", e)
        connection.rollback()
        print("Nothing changed")


print("\n--------------------------------------")
print("        NOW SWITCHING TO ORM          ")
print("--------------------------------------\n")



from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

engine = create_engine("mysql+pymysql://root:root@127.0.0.1:8889/northwind")
Session = sessionmaker(bind=engine)
session = Session()

Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"
    CategoryID = Column(Integer, primary_key=True)
    CategoryName = Column(String(50))
    products = relationship("Product", back_populates="category")


class Supplier(Base):
    __tablename = "suppliers"
    SupplierID = Column(Integer, primary_key=True)
    CompanyName = Column(String(100))
    products = relationship("Product", back_populates="supplier")

class Product(Base):
    __tablename__ = "products"

    ProductID = Column(Integer, primary_key=True)
    ProductName = Column(String(100))
    UnitPrice = Column(Float)

    CategoryID = Column(Integer, ForeignKey("categories.CategoryID"))
    SupplierID = Column(Integer, ForeignKey("suppliers.SupplierID"))

    category = relationship("Category", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")


def orm_simple_select():
    print("\nORM SELECT — First 5 Products:")
    products = session.query(Product).limit(5).all()
    for p in products:
        print(p.ProductName, p.UnitPrice)



def orm_join_demo():
    print("ORM SELECT FIRST 5")
    products = session.query(Product).limit(5).all()
    for p in products:
        print(p.ProductName, "-", p.category.CategoryName, "-", p.supplier.CompanyName)


def orm_filter_demo():
    print("ORM FILTER")
    cheap = session.query(Product).filter(Product.UnitPrice < 20).all()
    for c in cheap:
        print(c.ProductName, c.UnitPrice)


def orm_insert():
    print("\nORM INSERT:")
    new_cat = Category(CategoryName="ORM Category")
    session.add(new_cat)
    session.commit()
    print("Inserted category with ID:", new_cat.CategoryID)


def orm_update():
    print("\nORM UPDATE:")
    p = session.query(Product).filter_by(ProductID=1).first()
    p.UnitPrice += 5
    session.commit()
    print("Updated Product 1 price.")


def orm_delete():
    print("\nORM DELETE:")
    cat = session.query(Category).filter_by(CategoryName="ORM Category").first()
    if cat:
        session.delete(cat)
        session.commit()
        print("Deleted ORM Category.")
    else:
        print("ORM Category not found; nothing to delete.")

if __name__ == "__main__":

    # --- DBAPI Demo ---
    dbapi_simple_select()
    dbapi_parameterized_select()
    dbapi_insert()
    dbapi_update()
    dbapi_transaction_rollback()

    # --- ORM Demo ---
    orm_simple_select()
    orm_join_demo()
    orm_filter_demo()
    orm_insert()
    orm_update()
    orm_delete()

    print("\nDone.")


