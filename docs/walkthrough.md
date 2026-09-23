# Walkthrough: the 11 steps

Step-by-step explanation of the queries in `solutions/01_steps_basic.sql`: what each step asks, how the query works, what it returns and what it adds to the investigation.

The browser game runs on SQLite (sql.js); the same code runs on MySQL 8 in TablePlus.

---

## 0. The case and the data

**The crime (report #8):** Maximilian Krause (student_id 201), exchange student of the Global Data Lab, is found dead in **Room 204** on **21/09/2026** at 21:30. Estimated time of death: **between 19:00 and 20:00**. Room 204 has a badge reader.

**The tables:**

| Table | Contents | Used for |
|---|---|---|
| `crime_reports` | police reports | finding the case |
| `witness_statements` | what the witnesses said | the times to check |
| `access_log` | every swipe: badge, place, date, entry, exit | the timeline |
| `badges` | which student owns each badge | turning a badge into a person |
| `students` | name, surname, program | the names |
| `relationships` | who dated whom, and when it ended (`end_date NULL` = still together) | the motive |
| `grades`, `courses` | grades per course | dead ends and exercises |
| `lectures`, `attendance` | lectures and who attended | alibis |

**The trap:** `access_log.badge_id` has **no foreign key** to `badges`. The reader logs every card that is swiped, including cards that belong to nobody. That is where the killer hides.

**Witnesses for report 8:**
- Aurora Ferrari: at **18:45** Max was on the phone saying *"She chose me. Get over it."*, then went upstairs towards Room 204.
- Federica DeLuca: around **19:40** she heard a loud bang from Room 204; a few minutes later someone with a hood walked past quickly.
- Elena Petrova: around **20:00** she saw a guy in a grey Luiss hoodie leaving the building in a hurry.

---

## Step 1: The report
**Concepts:** `SELECT` · `WHERE` · `ORDER BY` · `LIMIT`

**Task:** find the **most recent** report for the `'Viale Romania'` campus. Exactly one row.

```sql
SELECT *
FROM crime_reports
WHERE campus = 'Viale Romania'
ORDER BY report_date DESC, report_time DESC
LIMIT 1;
```

**How it works**
- `WHERE campus = 'Viale Romania'` keeps only that campus (text values go in quotes).
- `ORDER BY report_date DESC, report_time DESC` sorts newest first: by date, and for equal dates by time.
- `LIMIT 1` keeps only the first row.

**Result:** report **8** (21/09/2026, 21:40, murder).

**Common mistake:** sorting by `report_date` only. On 21/09 there are **two** Viale Romania reports (#7 at 16:20, a theft, and #8 at 21:40). Without `report_time` the database may return the wrong one.

---

## Step 2: Room 204
**Concepts:** `INNER JOIN` · `DISTINCT`

**Task:** who swiped into Room 204 on 21/09? Each person once.

```sql
SELECT DISTINCT s.student_id, s.first_name, s.last_name
FROM access_log a
JOIN badges b   ON b.badge_id   = a.badge_id
JOIN students s ON s.student_id = b.student_id
WHERE a.location = 'Room 204'
  AND a.access_date = '2026-09-21';
```

**How it works**
- `a`, `b`, `s` are table aliases.
- The first `JOIN` links each swipe to its badge; the second links the badge to its student. Two joins: from a card to a name.
- `DISTINCT` removes duplicates: Max swiped **twice** (14:05 and 18:55).

**Result:** 5 students: 3 Giulia Rizzo, 4 Giorgia Marino, 5 Elisa Fontana, 6 Sara DeLuca, 201 Maximilian Krause.

**What matters:** `JOIN` (= `INNER JOIN`) keeps **only rows that find a match**. A swipe with a badge that is not in `badges` **silently disappears**. None of these five entered between 19:00 and 20:00, so something is missing.

---

## Step 3: The ghost badge
**Concepts:** `LEFT JOIN` · `IS NULL`

**Task:** find the Room 204 swipe on 21/09 whose `badge_id` **does not exist** in `badges`.

```sql
SELECT a.*
FROM access_log a
LEFT JOIN badges b ON b.badge_id = a.badge_id
WHERE b.badge_id IS NULL
  AND a.location = 'Room 204'
  AND a.access_date = '2026-09-21';
```

**How it works**
- `LEFT JOIN` keeps **every** row of the left table (`access_log`), even without a match on the right; the `badges` columns are then `NULL`.
- `WHERE b.badge_id IS NULL` keeps only the unmatched rows, the orphan badges.
- NULL is tested with `IS NULL`, never `= NULL` (which is never true).

**Result:** one row: badge **B-9147**, Room 204, in at **19:37:00**, out at **19:48:00**.

**For the case:** someone entered the room with an unregistered badge right around the bang at 19:40. Now the question is who used it.

**Equivalents:** `WHERE a.badge_id NOT IN (SELECT badge_id FROM badges)` or `NOT EXISTS (...)`. `NOT IN` breaks if the subquery returns a NULL.

---

## Step 4: The regulars
**Concepts:** `GROUP BY` · `COUNT` · `HAVING` · `ORDER BY`

**Task:** between 14 and 20 September, count each student's swipes into Room 204; keep those with **more than 3**, most frequent first.

```sql
SELECT s.student_id, s.first_name, s.last_name, COUNT(*) AS visits
FROM access_log a
JOIN badges b   ON b.badge_id   = a.badge_id
JOIN students s ON s.student_id = b.student_id
WHERE a.location = 'Room 204'
  AND a.access_date BETWEEN '2026-09-14' AND '2026-09-20'
GROUP BY s.student_id, s.first_name, s.last_name
HAVING COUNT(*) > 3
ORDER BY visits DESC;
```

**How it works**
- `BETWEEN ... AND ...` includes both ends.
- `GROUP BY` collapses all rows of the same student into one group; `COUNT(*)` counts the rows in each group.
- `HAVING` filters **groups**, after grouping. `WHERE` filters **rows**, before grouping, so `WHERE COUNT(*) > 3` is an error.

**Result:** 203 **Tommaso Arcuri (6)**, 204 Beatrice Solari (5), 5 Elisa Fontana (4).

**For the case:** Tommaso knows Room 204 better than anyone.

---

## Step 5: Her past
**Concepts:** subquery in `WHERE`

**Task:** find **every ex-partner** of the victim's current girlfriend. Each couple is stored twice (once per side); `end_date NULL` = still together.

```sql
SELECT r.student_id, s.first_name, s.last_name, r.start_date, r.end_date
FROM relationships r
JOIN students s ON s.student_id = r.student_id
WHERE r.partner_id = (SELECT partner_id FROM relationships
                      WHERE student_id = 201 AND end_date IS NULL)
  AND r.end_date IS NOT NULL;
```

**How it works**
- The subquery runs first and returns Max's current partner: **202, Ginevra Loreti**.
- The outer query becomes "rows whose partner is Ginevra **and** the relationship ended", i.e. her exes.
- The subquery must return **one value**, because it is used with `=`.

**Result:** 203 **Tommaso Arcuri** (14/02/2024 → 30/07/2026) and 205 Federico Neri (2022 → 2023).

**For the case:** Ginevra left Tommaso on **30 July 2026** and started dating Max on **20 August**. *"She chose me. Get over it."* now makes sense: **the motive is jealousy**.

---

## Step 6: Report cards
**Concepts:** subquery in `FROM` (derived table)

**Task:** compute each student's **average grade**, then keep those **below 22**.

```sql
SELECT t.student_id, s.first_name, s.last_name, t.avg_grade
FROM (SELECT student_id, AVG(grade) AS avg_grade
      FROM grades
      GROUP BY student_id) AS t
JOIN students s ON s.student_id = t.student_id
WHERE t.avg_grade < 22;
```

**How it works**
- The subquery in `FROM` builds a temporary table (`student_id`, `avg_grade`).
- A derived table **must** have an alias (`AS t`).
- It is then used like any table: joined to `students`, filtered with `WHERE`.

**Result:** 204 Beatrice Solari (18.75), 209 Hugo Lefevre (21.5), 213 Jonas Weber (21.0).

**For the case:** a "grades" lead (envy of Max, who has 30 everywhere). A **dead end**: Beatrice has the worst grades but an alibi (step 9).

---

## Step 7: Points behind
**Concepts:** subquery in `SELECT` (scalar subquery)

**Task:** for every Machine Learning grade **except the victim's**, show how many points it is below Max's Machine Learning grade.

```sql
SELECT g.student_id, g.grade,
       (SELECT grade FROM grades WHERE student_id = 201 AND course_id = 1) - g.grade AS points_behind
FROM grades g
WHERE g.course_id = 1
  AND g.student_id <> 201;
```

**How it works**
- Machine Learning is `course_id = 1` (see `courses`).
- The subquery in `SELECT` returns **one number**, Max's grade (30).
- Each row computes `30 - grade`. `<>` means "not equal".

**Result:** 15 rows, e.g. Tommaso 29 → 1 point behind, Beatrice 18 → 12 points behind.

---

## Step 8: Last in class
**Concepts:** **correlated** subquery

**Task:** for **each course**, find the student(s) with the **lowest grade**. Each student once.

```sql
SELECT DISTINCT s.student_id, s.first_name, s.last_name
FROM grades g
JOIN students s ON s.student_id = g.student_id
WHERE g.grade = (SELECT MIN(g2.grade)
                 FROM grades g2
                 WHERE g2.course_id = g.course_id);
```

**How it works**
- The subquery is **correlated**: it uses `g.course_id` from the outer row, so it is re-evaluated for every row.
- `g` and `g2` are two aliases of the **same table**.
- `DISTINCT` because Beatrice is last in several courses.

**Result:** 204 Beatrice Solari (last in ML, Econometrics, Marketing Analytics) and 211 Pablo Ortega (last in Databases).

**At scale:** re-evaluating `MIN()` for every row is quadratic. See the README for the benchmark against `RANK() OVER (PARTITION BY course_id)`.

---

## Step 9: Alibis
**Concepts:** `UNION`

**Task:** one list of **everyone with an alibi** for the whole **19:37–19:48** window on 21/09, with a column saying which alibi:
- students attending a lecture that covered the whole window → `'lecture'`
- **UNION** students in the `'Library'` or `'Gym'` for the whole window → the location.

```sql
SELECT att.student_id, 'lecture' AS alibi
FROM attendance att
JOIN lectures l ON l.lecture_id = att.lecture_id
WHERE l.lecture_date = '2026-09-21'
  AND l.start_time <= '19:37:00' AND l.end_time >= '19:48:00'
UNION
SELECT b.student_id, a.location AS alibi
FROM access_log a
JOIN badges b ON b.badge_id = a.badge_id
WHERE a.access_date = '2026-09-21'
  AND a.location IN ('Library', 'Gym')
  AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00';
```

**How it works**
- The window comes from step 3.
- "For the whole window" = started at or before 19:37 **and** ended at or after 19:48.
- `UNION` stacks the two lists and **removes duplicates** (`UNION ALL` keeps them). Both sides need the same number of columns.

**Result:** 15 people. 11 in a lecture (Databases 18:30–20:30: students 30–39 and **Beatrice Solari 204**), 3 in the Library (12, 40, 206), 1 in the Gym (41).

**For the case:** Beatrice, the "obvious" suspect (Max's ex, a Room 204 regular, low grades), is **cleared**.

---

## Step 10: No alibi
**Concepts:** `EXCEPT`

**Task:** everyone **inside the building** (`'Main Entrance'`) for the whole window, **EXCEPT** those in a lecture, **EXCEPT** those in the Library or Gym.

```sql
SELECT b.student_id
FROM access_log a
JOIN badges b ON b.badge_id = a.badge_id
WHERE a.location = 'Main Entrance' AND a.access_date = '2026-09-21'
  AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00'
EXCEPT
SELECT att.student_id
FROM attendance att
JOIN lectures l ON l.lecture_id = att.lecture_id
WHERE l.lecture_date = '2026-09-21'
  AND l.start_time <= '19:37:00' AND l.end_time >= '19:48:00'
EXCEPT
SELECT b.student_id
FROM access_log a
JOIN badges b ON b.badge_id = a.badge_id
WHERE a.access_date = '2026-09-21'
  AND a.location IN ('Library', 'Gym')
  AND a.entry_time <= '19:37:00' AND a.exit_time >= '19:48:00';
```

**How it works**
- `EXCEPT` is set difference: the first list minus the second, minus the third.
- MySQL supports `EXCEPT` from 8.0.31; `NOT EXISTS` works on older versions.

**Who drops out:**
- Simone Colombo leaves the building at 19:45, **before** B-9147 leaves the room (19:48).
- Anna D'Angelo arrives at 19:40, **after** B-9147 entered (19:37).
- Aurora Ferrari left at 19:10.
- Everyone else inside has an alibi.

**Result:** **one row: 203, Tommaso Arcuri**, in the building from 18:40:07 to 20:05:58 with no alibi. He leaves at 20:05, which matches the witness who saw someone rush out around 20:00.

---

## Step 11: Case closed
**Concepts:** `CREATE TABLE` · `INSERT`

```sql
CREATE TABLE solution (
  first_name  VARCHAR(50),
  last_name   VARCHAR(50),
  motive      VARCHAR(200),
  murder_time TIME
);
INSERT INTO solution VALUES
  ('Tommaso', 'Arcuri', 'Love jealousy: Ginevra left him for Maximilian', '19:37:00');
```

- `VARCHAR(n)` = text up to n characters; `TIME` = a time of day.
- `INSERT ... VALUES` values follow the column order.
- `murder_time` is the entry of B-9147 (step 3).
- If the table already exists, start with `DROP TABLE IF EXISTS solution;`.

---

## Summary

| | |
|---|---|
| **WHO** | Tommaso Arcuri, student_id 203 |
| **HOW** | Unregistered badge **B-9147**, Room 204, 21/09/2026, **19:37–19:48** (bang at ~19:40) |
| **WHY** | Jealousy: Ginevra Loreti left him on 30/07/2026 and started dating Max on 20/08 |
| **PROOF** | Step 3 (ghost badge) + step 5 (motive) + step 10 (only one without an alibi) |

**Dead ends:**
- **Beatrice Solari**: Max's ex, Room 204 regular, lowest grades, but in a lecture 18:30–20:30.
- **Federico Neri**: another ex of Ginevra, but not in the building, and it ended in 2023.
- **Grades** (steps 6–8): no link to the murder.
- **B-0000**: another ghost card, but in the gym on 16/09.
- **Report #10** (badge holder lost at Villa Blanc): different campus.

## Glossary

| Concept | In one line |
|---|---|
| `WHERE` | filters rows |
| `ORDER BY ... DESC` | sorts, largest/newest first |
| `LIMIT n` | keeps the first n rows |
| `INNER JOIN` | combines tables, keeps only matching rows |
| `LEFT JOIN` | keeps every left row; missing matches become NULL |
| `IS NULL` | the only correct test for missing values |
| `DISTINCT` | removes duplicates |
| `GROUP BY` + `COUNT/AVG/MIN` | one value per group |
| `HAVING` | filters groups (after `GROUP BY`) |
| subquery in `WHERE` | a query's result used as a comparison value |
| subquery in `FROM` | a temporary table (needs an alias) |
| subquery in `SELECT` | a single value shown as a column |
| correlated subquery | uses a value from the outer row, re-evaluated per row |
| `UNION` | stacks two lists (no duplicates) |
| `EXCEPT` | first list minus the second |
| `CREATE TABLE` / `INSERT` | create a table / add rows |
