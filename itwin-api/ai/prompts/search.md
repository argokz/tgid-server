Задача: превратить фразу пользователя ГИС тепловых сетей в структурированный запрос, который выполнит сервер. SQL не пиши — только поля схемы.

Виды запроса (kind):
- node — найти узел/камеру по имени или коду (ТК-12, МТК 3-47, УТ-5-34, «камера 15а»);
- line — найти участок между узлами («участок ТК-12 — ТК-13», «труба от 3-47 до 3-49»);
- consumer — список потребителей по диагностике нагрузок: diagnostic = zero_load (нулевая нагрузка), closed (закрыт), disconnected (отключён), not_calculated (не рассчитан); consumer_type = generalized | real;
- source — найти источник тепла по имени (ТЭЦ-1, котельная …);
- tool — открыть инструмент веба: ключи defect (нарушения), shurf (шурфовки), inspection (осмотры), repair (ремонты), pressureTest (опрессовки), corrosionIndicator (индикаторы коррозии), technicalCondition (ТУ), alseko (АЛСЕКО), electricalNetwork (электросеть), heatLoss (теплопотери), temperatureGraph (температурные графики), consumerLoad (диагностика нагрузок), networkQueries (запросы по сети Zap), regimeAnalysis (анализ режима), outageSimulation (локализация аварий), throttlingCalculator (калькулятор дросселирования), hydraulicThematic (гидравлический режим на карте), wearIndex (износ и план ремонтов), dataQuality (качество данных), excelReports (отчёты Excel), pumpEquipment, networkArmature, networkRegulator, networkBypass, networkDiaphragm, elevator (оборудование);
- unknown — не удалось понять.

Правила:
- fragment_id — число из фразы («во фрагменте 74», «фр. 74»), иначе null.
- text — имя/код объекта для поиска подстрокой, очищенное от слов «узел», «камера», «ТК», «участок», если они не часть кода; для line — text = первый узел, text2 = второй.
- Для tool: tool_key из списка, scope_text — что передать инструменту (например имя источника или номер).
- Если фраза про потребителей без нагрузки/закрытых/отключённых — kind=consumer с diagnostic.
- confidence 0..1 — насколько уверен; при unknown — 0, и в note объясни, что уточнить.
