def mo1():
    q = '''

    select 
    id,
    shape,
--    priznak_truboprovoda,
    case when priznak_truboprovoda <> 3 then purposeTypesID else null end as purposeTypesID_P,
    case when priznak_truboprovoda <> 3 then armatureTypesID else null end as armatureTypesID_P,
    case when priznak_truboprovoda <> 3 then designTypesID else null end as designTypesID_P,
    case when priznak_truboprovoda <> 3 then materialTypesID else null end as materialTypesID_P,
    case when priznak_truboprovoda <> 3 then constructionTypesID else null end as constructionTypesID_P,
    case when priznak_truboprovoda <> 3 then diametr else null end as diametr_P,

    case when priznak_truboprovoda <> 2 then purposeTypesID else null end as purposeTypesID_O,
    case when priznak_truboprovoda <> 2 then armatureTypesID else null end as armatureTypesID_O,
    case when priznak_truboprovoda <> 2 then designTypesID else null end as designTypesID_O,
    case when priznak_truboprovoda <> 2 then materialTypesID else null end as materialTypesID_O,
    case when priznak_truboprovoda <> 2 then constructionTypesID else null end as constructionTypesID_O,
    case when priznak_truboprovoda <> 2 then diametr else null end as diametr_O,

    case when priznak_truboprovoda <> 3 then diam_reg else 0 end as diam_reg_P,
    case when priznak_truboprovoda <> 3 then diam_sec else 0 end as diam_sec_P,
    case when priznak_truboprovoda <> 3 then diam_v else 0 end as diam_v_P,
    case when priznak_truboprovoda <> 3 then diam_dr else 0 end as diam_dr_P,
    case when priznak_truboprovoda <> 3 then diam_dt else 0 end as diam_dt_P,
    case when priznak_truboprovoda <> 3 then diam_per else 0 end as diam_per_P,

    case when priznak_truboprovoda <> 2 then diam_reg else 0 end as diam_reg_O,
    case when priznak_truboprovoda <> 2 then diam_sec else 0 end as diam_sec_O,
    case when priznak_truboprovoda <> 2 then diam_v else 0 end as diam_v_O,
    case when priznak_truboprovoda <> 2 then diam_dr else 0 end as diam_dr_O,
    case when priznak_truboprovoda <> 2 then diam_dt else 0 end as diam_dt_O,
    case when priznak_truboprovoda <> 2 then diam_per else 0 end as diam_per_O,


    case when priznak_truboprovoda <> 3 then cnt_reg else 0 end as cnt_reg_P,
    case when priznak_truboprovoda <> 3 then cnt_sec else 0 end as cnt_sec_P,
    case when priznak_truboprovoda <> 3 then cnt_v else 0 end as cnt_v_P,
    case when priznak_truboprovoda <> 3 then cnt_dr else 0 end as cnt_dr_P,
    case when priznak_truboprovoda <> 3 then cnt_dt else 0 end as cnt_dt_P,
    case when priznak_truboprovoda <> 3 then cnt_per else 0 end as cnt_per_P,

    case when priznak_truboprovoda <> 2 then cnt_reg else 0 end as cnt_reg_O,
    case when priznak_truboprovoda <> 2 then cnt_sec else 0 end as cnt_sec_O,
    case when priznak_truboprovoda <> 2 then cnt_v else 0 end as cnt_v_O,
    case when priznak_truboprovoda <> 2 then cnt_dr else 0 end as cnt_dr_O,
    case when priznak_truboprovoda <> 2 then cnt_dt else 0 end as cnt_dt_O,
    case when priznak_truboprovoda <> 2 then cnt_per else 0 end as cnt_per_O


    from (

    select 
    z.id,
    z.shape,
    z.priznak_truboprovoda,
    coalesce(z.purposeTypesID, 2) as purposeTypesID,
    z.armatureTypesID,
    z.designTypesID,
    z.materialTypesID,
    z.constructionTypesID,

    case z.purposeTypesID when 1 then 0 else z.diametr end as diam_reg,
    case z.purposeTypesID when 1 then 0 else 1 end as cnt_reg,

    case z.purposeTypesID when 1 then z.diametr else 0 end as diam_sec,
    case z.purposeTypesID when 1 then 1 else 0 end as cnt_sec,

    0 as diam_v,
    0 as cnt_v,

    0 as diam_dr,
    0 as cnt_dr,

    0 as diam_dt,
    0 as cnt_dt,

    0 as diam_per,
    0 as cnt_per,

    z.diametr

    from zapornaya_armatura z

    UNION ALL

    select 
    z.id,
    z.shape,
    z.priznak_truboprovoda,
    z.purposeTypesID,
    z.armatureTypesID,
    z.designTypesID,
    z.materialTypesID,
    z.constructionTypesID,

    0 as diam_reg,
    0 as cnt_reg,

    0 as diam_sec,
    0 as cnt_sec,

    z.diametr as diam_v,
    1 as cnt_v,

    0 as diam_dr,
    0 as cnt_dr,

    0 as diam_dt,
    0 as cnt_dt,

    0 as diam_per,
    0 as cnt_per,
    
    z.diametr


    from vozdushnik z

    UNION ALL

    select 
    z.id,
    z.shape,
    z.priznak_truboprovoda,
    z.purposeTypesID,
    z.armatureTypesID,
    z.designTypesID,
    z.materialTypesID,
    z.constructionTypesID,

    0 as diam_reg,
    0 as cnt_reg,

    0 as diam_sec,
    0 as cnt_sec,

    0 as diam_v,
    0 as cnt_v,

    z.diametr as diam_dr,
    1 as cnt_dr,

    0 as diam_dt,
    0 as cnt_dt,

    0 as diam_per,
    0 as cnt_per,
    
    z.diametr

    from drenazhnyy_kran z

    UNION ALL

    select 
    z.id,
    z.shape,
    z.priznak_truboprovoda,
    7 as purposeTypesID,
    z.armatureTypesID,
    z.designTypesID,
    z.materialTypesID,
    z.constructionTypesID,

    0 as diam_reg,
    0 as cnt_reg,

    0 as diam_sec,
    0 as cnt_sec,

    0 as diam_v,
    0 as cnt_v,

    0 as diam_dr,
    0 as cnt_dr,

    0 as diam_dt,
    0 as cnt_dt,

    diametr_peremychki as diam_per,
    1 as cnt_per,
    
    diametr_peremychki as diametr

    from peremychki z

    ) obj
    '''
    return q
