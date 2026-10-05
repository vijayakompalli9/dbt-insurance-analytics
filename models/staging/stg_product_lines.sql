select
    upper(trim(product_line_code)) as product_line_code,
    trim(product_line_name) as product_line_name,
    trim(line_of_business) as line_of_business,
    cast(target_loss_ratio as decimal(5, 3)) as target_loss_ratio,
    cast(is_active as boolean) as is_active
from {{ raw_source('product_lines') }}
