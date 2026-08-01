from flask import Flask, render_template, request, redirect, flash
from app.database import create_table, get_connection

app = Flask(__name__)

app.secret_key = "student_management_secret_key"

create_table()


@app.route("/")
def home():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT COUNT(*) FROM students")
    total_students = cursor.fetchone()[0]

    cursor.execute("SELECT AVG(cgpa) FROM students")
    avg_cgpa = cursor.fetchone()[0]

    cursor.execute("SELECT MAX(cgpa) FROM students")
    highest_cgpa = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(cgpa) FROM students")
    lowest_cgpa = cursor.fetchone()[0]

    connection.close()

    if avg_cgpa is None:
        avg_cgpa = 0
        highest_cgpa = 0
        lowest_cgpa = 0

    return render_template(
        "index.html",
        total_students=total_students,
        avg_cgpa=round(avg_cgpa, 2),
        highest_cgpa=highest_cgpa,
        lowest_cgpa=lowest_cgpa
    )


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/students")
def students():

    search = request.args.get("search", "")
    sort = request.args.get("sort", "name_asc")

    connection = get_connection()
    cursor = connection.cursor()

    query = "SELECT * FROM students"
    conditions = []
    params = []

    if search:
        conditions.append("name LIKE ?")
        params.append(f"%{search}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    sort_options = {
        "name_asc": "name ASC",
        "name_desc": "name DESC",
        "age_asc": "age ASC",
        "age_desc": "age DESC",
        "cgpa_asc": "cgpa ASC",
        "cgpa_desc": "cgpa DESC"
    }

    query += " ORDER BY " + sort_options.get(sort, "name ASC")

    cursor.execute(query, params)

    students = cursor.fetchall()

    connection.close()

    return render_template(
        "students.html",
        students=students,
        search=search,
        sort=sort
    )


@app.route("/add", methods=["GET", "POST"])
def add_student():

    if request.method == "POST":

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO students(name, age, department, cgpa)
            VALUES (?, ?, ?, ?)
            """,
            (
                request.form["name"],
                request.form["age"],
                request.form["department"],
                request.form["cgpa"]
            )
        )

        connection.commit()
        connection.close()

        flash("Student added successfully!", "success")

        return redirect("/students")

    return render_template("add_student.html")


@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_student(id):

    connection = get_connection()
    cursor = connection.cursor()

    if request.method == "POST":

        cursor.execute(
            """
            UPDATE students
            SET
                name=?,
                age=?,
                department=?,
                cgpa=?
            WHERE id=?
            """,
            (
                request.form["name"],
                request.form["age"],
                request.form["department"],
                request.form["cgpa"],
                id
            )
        )

        connection.commit()
        connection.close()

        flash("Student updated successfully!", "warning")

        return redirect("/students")

    cursor.execute("SELECT * FROM students WHERE id=?", (id,))
    student = cursor.fetchone()

    connection.close()

    return render_template("edit_student.html", student=student)


@app.route("/delete/<int:id>")
def delete_student(id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("DELETE FROM students WHERE id=?", (id,))

    connection.commit()
    connection.close()

    flash("Student deleted successfully!", "danger")

    return redirect("/students")


if __name__ == "__main__":
    app.run(debug=True)