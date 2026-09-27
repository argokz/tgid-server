-- gid6 excel2/sql2/Организации.sql (шаблон gst, лист 4). Справочник общий, без фрагмента.
SELECT 'РЭ' AS re, name, sign, phone, managerphone, street, housenumber
  FROM organizations
 ORDER BY name, id
