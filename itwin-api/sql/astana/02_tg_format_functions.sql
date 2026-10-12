-- Функции подписей слоёв GeoServer uzel/heatpipesections (NAPOR, DLINA…), копия из almatygid.
-- В базе Астаны из десктопа их нет.

CREATE OR REPLACE FUNCTION public.tg_format(label1 text, value1 double precision, max_decimals integer DEFAULT 2)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
    v1 TEXT := tg_format_float(value1, max_decimals);
BEGIN
    IF value1 = 0 THEN
        RETURN '';
    END IF;

    IF label1 != '' THEN
        label1 = label1 || '=';
    END IF;    


    RETURN label1 || v1 || CHR(10);
END;
$function$
;

CREATE OR REPLACE FUNCTION public.tg_format_check(yes boolean, label1 text, value1 double precision, max_decimals integer DEFAULT 2)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    IF NOT yes THEN
        RETURN '';
    END IF;

    RETURN tg_format(label1, value1, max_decimals);
END;
$function$
;

CREATE OR REPLACE FUNCTION public.tg_format_compare(label1 text, value1 double precision, value2 double precision, max_decimals integer DEFAULT 2)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
    v1 TEXT := tg_format_float(value1, max_decimals);
    v2 TEXT := tg_format_float(value2, max_decimals);
BEGIN
    IF ABS(value1 - value2) < 1e-9 THEN  -- сравнение с погрешностью
        RETURN label1 || '=' || v1 || CHR(10);
    ELSE
        RETURN label1 || 'п=' || v1 || '; ' || label1 || 'о=' || v2 || CHR(10);
    END IF;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.tg_format_compare_check(yes boolean, label1 text, value1 double precision, value2 double precision, max_decimals integer DEFAULT 2)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    IF NOT yes THEN
        RETURN '';
    END IF;
    
    RETURN tg_format_compare(label1, value1, value2, max_decimals);

END;
$function$
;

CREATE OR REPLACE FUNCTION public.tg_format_float(value double precision, max_decimals integer DEFAULT 3)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
    abs_val FLOAT := ABS(value);
    decimals INT;
    formatted TEXT;
BEGIN
    -- Определяем количество знаков после запятой
    IF abs_val >= 100 THEN
        decimals := 0;
    ELSIF abs_val >= 100 THEN
        decimals := 1;
    ELSIF abs_val >= 10 THEN
        decimals := 2;
    ELSIF abs_val >= 1 THEN
        decimals := 3;
    ELSE
        decimals := max_decimals;
    END IF;

    -- Округляем
    formatted := ROUND(value::numeric, decimals)::TEXT;

    -- Убираем лишние нули и точку (например, 123.00 → 123)
    formatted := TRIM(TRAILING '.' FROM TRIM(TRAILING '0' FROM formatted));

    RETURN formatted;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.tg_format2(value1 double precision, value2 double precision, max_decimals integer DEFAULT 2)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
DECLARE
    v1 TEXT := tg_format_float(value1, max_decimals);
    v2 TEXT := tg_format_float(value2, max_decimals);
BEGIN
    IF value1 = 0 and value2 = 0 THEN
        RETURN '';
    END IF;

    RETURN v1 || '; ' || v2 || CHR(10);
END;
$function$
;

CREATE OR REPLACE FUNCTION public.tg_format2_check(yes boolean, value1 double precision, value2 double precision, max_decimals integer DEFAULT 2)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    IF NOT yes THEN
        RETURN '';
    END IF;

    RETURN tg_format2(value1, value2, max_decimals);
END;
$function$
;

CREATE OR REPLACE FUNCTION public.tg_format2_check(yes boolean, label1 text, value1 double precision, value2 double precision, max_decimals integer DEFAULT 2)
 RETURNS text
 LANGUAGE plpgsql
 IMMUTABLE
AS $function$
BEGIN
    IF NOT yes THEN
        RETURN '';
    END IF;

    RETURN tg_format2(value1, value2, max_decimals);
END;
$function$
;
