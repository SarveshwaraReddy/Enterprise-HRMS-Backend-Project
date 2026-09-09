from django.db import migrations


def repair_legacy_leave_type_column(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    table_name = schema_editor.quote_name("leave_management_leaverequest")
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = %s
              AND column_name IN ('leave_type', 'leave_type_id')
            """,
            ["leave_management_leaverequest"],
        )
        columns = {row[0] for row in cursor.fetchall()}

        if "leave_type_id" in columns and "leave_type" not in columns:
            cursor.execute(
                """
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = %s::regclass
                  AND contype = 'f'
                  AND EXISTS (
                      SELECT 1
                      FROM unnest(conkey) AS key_column
                      JOIN pg_attribute AS attribute
                        ON attribute.attrelid = conrelid
                       AND attribute.attnum = key_column
                      WHERE attribute.attname = 'leave_type_id'
                  )
                """,
                ["leave_management_leaverequest"],
            )
            for (constraint_name,) in cursor.fetchall():
                cursor.execute(
                    f"ALTER TABLE {table_name} DROP CONSTRAINT "
                    f"{schema_editor.quote_name(constraint_name)}"
                )
            cursor.execute(
                f"ALTER TABLE {table_name} "
                "ALTER COLUMN \"leave_type_id\" TYPE varchar(20) "
                "USING \"leave_type_id\"::varchar(20)"
            )
            cursor.execute(
                f"ALTER TABLE {table_name} "
                "RENAME COLUMN \"leave_type_id\" TO \"leave_type\""
            )


class Migration(migrations.Migration):
    dependencies = [
        ("leave_management", "0002_leaverequest_leave_emp_status_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(repair_legacy_leave_type_column, migrations.RunPython.noop),
    ]