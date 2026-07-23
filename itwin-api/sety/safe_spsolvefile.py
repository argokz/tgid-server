import numpy as np
import warnings
from scipy.sparse.linalg import spsolve
from scipy.sparse import issparse

# универсальный импорт MatrixRankWarning (разные версии SciPy)
try:
    from scipy.sparse.linalg import MatrixRankWarning
except ImportError:
    from scipy.linalg import MatrixRankWarning


def dump_system(A, b, t, max_rows=10):
    A = A.tocoo()  # переводим в удобный формат (строка, столбец, значение)
    rows = A.shape[0]


    print(len(b) * 14 * '-')
    for i in range(min(rows, max_rows)):
        # все элементы этой строки
        mask = A.row == i
        cols = A.col[mask]
        vals = A.data[mask]

        def form(d):
            if d == 0.00000000001:
                return f'{'e':>10}'

            s = f'{d:10.3f}'
            if len(s) > 10:
                s = f'{d:10.3e}'

            return s
            

        parts = [f"{c:4d}:{form(vals[j])}" for j, c in enumerate(cols)]
        row_str = " ".join(parts) if parts else "(пусто)"

        b_val = b[i] if b is not None and i < len(b) else None

        b_val_text = f'{b_val:10.3f}'
        if b[i] == 0:
            b_val_text = f'{0:10d}'

        t_val = t[i] if t is not None and i < len(b) else None
            

        print(f"{i:4d}| B:{b_val_text}| t:{form(t_val)} | {row_str}")


def check_nonzero_values(matrix):
    data = matrix.data  # только ненулевые элементы

    if data.size == 0:
        print("В матрице вообще нет ненулевых значений")
        return

    has_nan = np.isnan(data).any()
    has_inf = np.isinf(data).any()

    print("Есть NaN среди ненулевых:", has_nan)
    print("Есть Inf среди ненулевых:", has_inf)
    print("Минимальное ненулевое:", data.min())
    print("Максимальное ненулевое:", data.max())

def check_vector(b):
    if b.size == 0:
        print("Вектор пустой")
        return

    has_nan = np.isnan(b).any()
    has_inf = np.isinf(b).any()

    print("Есть NaN:", has_nan)
    print("Есть Inf:", has_inf)
    print("Минимальное значение:", b.min())
    print("Максимальное значение:", b.max())


def _find_zero_rows_cols(A):
    """Найти нулевые строки и столбцы для matrix/array форматов."""
    if hasattr(A, "getnnz"):  # csr_matrix / csc_matrix
        zero_rows = np.where(A.getnnz(axis=1) == 0)[0]
        zero_cols = np.where(A.getnnz(axis=0) == 0)[0]
    else:  # csr_array / csc_array
        zero_rows = np.where(np.asarray((A != 0).sum(axis=1)).ravel() == 0)[0]
        zero_cols = np.where(np.asarray((A != 0).sum(axis=0)).ravel() == 0)[0]
    return zero_rows, zero_cols


def safe_spsolve(A, b, max_dense_size=200):
    """Решает Ax=b через spsolve и делает диагностику сингулярности."""
    if not issparse(A):
        raise TypeError("A must be a scipy sparse matrix/array")

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always", MatrixRankWarning)
        x = spsolve(A, b)
        singular = any(issubclass(wi.category, MatrixRankWarning) for wi in w)

    # Проверка на nan/inf
    if np.any(np.isnan(x)) or np.any(np.isinf(x)):
        singular = True

    if singular:
        print(" Matrix appears singular or ill-conditioned")

#        dump_system(A, b, b, 20)


#        print(b)
        if False:

            check_nonzero_values(A)
            check_vector(b) 

            # 1. Нулевые строки/столбцы
            zr, zc = _find_zero_rows_cols(A)
            if len(zr):
                print("Zero rows:", zr)
            if len(zc):
                print("Zero cols:", zc)

            # 2. Ранг и обусловленность (если матрица не слишком большая)
            if A.shape[0] <= max_dense_size:
                dense_A = A.toarray()
                rank = np.linalg.matrix_rank(dense_A)
                cond = np.linalg.cond(dense_A)
                print(f"Rank: {rank}/{A.shape[0]}")
                print(f"Condition number: {cond:.2e}")
            else:
                print(f"Matrix too large for dense rank/cond check {A.shape[0]}")

#        dump_system(A, b, 20000)
#        exit(1)

    return x, not singular
