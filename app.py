from flask import Flask, render_template, request, redirect, flash, Response, url_for
import os
from werkzeug.utils import secure_filename
from app.database import create_table, get_connection
import math
import csv
import io

app = Flask(__name__)

app.secret_key = "student_management_secret_key"

UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )

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
    department = request.args.get("department", "")
    page = request.args.get("page", 1, type=int)

    per_page = 5
    offset = (page - 1) * per_page

    connection = get_connection()
    cursor = connection.cursor()

    where_clause = ""
    params = []

    conditions = []

    if search:
        conditions.append("name LIKE ?")
        params.append(f"%{search}%")

    if department:
        conditions.append("department = ?")
        params.append(department)

    if conditions:
        where_clause = " WHERE " + " AND ".join(conditions)

    cursor.execute(
        "SELECT COUNT(*) FROM students" + where_clause,
        params
    )

    total_students = cursor.fetchone()[0]
    total_pages = max(1, math.ceil(total_students / per_page))

    sort_options = {
        "name_asc": "name ASC",
        "name_desc": "name DESC",
        "age_asc": "age ASC",
        "age_desc": "age DESC",
        "cgpa_asc": "cgpa ASC",
        "cgpa_desc": "cgpa DESC"
    }

    query = (
        "SELECT * FROM students"
        + where_clause
        + " ORDER BY "
        + sort_options.get(sort, "name ASC")
        + " LIMIT ? OFFSET ?"
    )

    cursor.execute(
        query,
        params + [per_page, offset]
    )

    students = cursor.fetchall()

    connection.close()

    return render_template(
        "students.html",
        students=students,
        search=search,
        sort=sort,
        department=department,
        page=page,
        total_pages=total_pages
    )

@app.route("/student/<int:id>")
def student_profile(id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM students WHERE id=?",
        (id,)
    )

    student = cursor.fetchone()

    connection.close()

    if student is None:
        flash("Student not found.", "danger")
        return redirect("/students")

    return render_template(
        "student_profile.html",
        student=student
    )

@app.route("/add", methods=["GET", "POST"])
def add_student():

    if request.method == "POST":

        name = request.form["name"]
        age = request.form["age"]
        department = request.form["department"]
        cgpa = request.form["cgpa"]

        photo = request.files.get("photo")

        filename = None

        if photo and allowed_file(photo.filename):

            filename = secure_filename(photo.filename)

            photo.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    filename
                )
            )

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO students(
                name,
                age,
                department,
                cgpa,
                photo
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                name,
                age,
                department,
                cgpa,
                filename
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

@app.route("/export")
def export_csv():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, age, department, cgpa
        FROM students
        ORDER BY id
    """)

    students = cursor.fetchall()

    connection.close()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "ID",
        "Name",
        "Age",
        "Department",
        "CGPA"
    ])

    for student in students:

        writer.writerow([
            student["id"],
            student["name"],
            student["age"],
            student["department"],
            student["cgpa"]
        ])

    csv_data = output.getvalue()

    output.close()

    return Response(
        csv_data,
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=students.csv"
        }
    )

@app.route("/import", methods=["GET", "POST"])
def import_csv():

    if request.method == "POST":

        file = request.files.get("csv_file")

        if not file or file.filename == "":
            flash("Please choose a CSV file.", "danger")
            return redirect(url_for("import_csv"))

        stream = io.StringIO(file.stream.read().decode("UTF8"), newline="")
        reader = csv.reader(stream)

        next(reader, None)

        connection = get_connection()
        cursor = connection.cursor()

        count = 0

        for row in reader:

            if len(row) < 5:
                continue

            cursor.execute(
                """
                INSERT INTO students(name, age, department, cgpa)
                VALUES (?, ?, ?, ?)
                """,
                (
                    row[1],
                    row[2],
                    row[3],
                    row[4]
                )
            )

            count += 1

        connection.commit()
        connection.close()

        flash(f"{count} students imported successfully!", "success")

        return redirect("/students")

    return render_template("import_students.html")

if __name__ == "__main__":
    app.run(debug=True)