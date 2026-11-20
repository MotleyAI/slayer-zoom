# Jaffle Shop: business context

## Who asks

The finance lead of a small chain of cafés that sell jaffles (toasted sandwiches) and drinks. They want the number
first, then where it comes from, then what is changing. They read dollars, not cents, and percentages to one
decimal place.

## Glossary

- **Shop, café, location, branch**: a store (`stores`). Orders link to their store, so split orders by `stores.name`.
- **Region**: a group of stores (`regions`, joined from `stores`).
- **Revenue, sales, takings**: `orders.total_revenue`, gross sales including tax. It counts refunded and cancelled
  orders too, because those keep their order total. Say "gross" when that matters.
- **Net sales**: `orders.net_sales`, sales before tax.
- **Orders**: `orders.order_count`. **Customers**: `orders.unique_customers` for customers who ordered.
- **Average order, basket, ticket**: `orders.avg_order_value`.
- **Units, items sold**: `items.units_sold`, one row per unit. Items join to orders (and through them to stores)
  and to products.
- **Product line, category**: `products.type`, either `jaffle` or `beverage`. **Product**: `products.name`.
- **Status**: `orders.status` is `completed`, `refunded` or `cancelled`.

## Calendar

- The fiscal year is the calendar year. "Year to date" (YTD) runs from 1 January of the current year to today.
- Today's data is partial: the last day in the data is today. Treat the current month as incomplete, and compare
  complete months when you compare periods.

## Caveats

- **There is no revenue per product or product line.** `products.price` summed from `items` repeats across the
  join and is wrong. Use `items.units_sold` for product mix, and say so.
- **The chain grew during the data.** Philadelphia has orders from November 2024, Brooklyn from June 2025, and
  Chicago and San Francisco only from July 2026. Two stores in `stores` have no orders yet. Year-on-year growth
  mixes new stores with like-for-like growth, so say that when you show it.
- Orders start in November 2024, so a full prior year exists only for 2025.
- Refunded and cancelled orders are a few percent of orders. Split by `orders.status` only when the question is
  about quality or refunds.
