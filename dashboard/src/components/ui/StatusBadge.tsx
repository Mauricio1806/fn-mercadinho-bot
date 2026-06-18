/**
 * StatusBadge — usa as classes .badge-* já definidas no index.css.
 */

import type { OrderStatus } from "@/lib/types";
import { STATUS_LABEL } from "@/lib/format";

export function StatusBadge({ status }: { status: OrderStatus }) {
  return <span className={`badge badge-${status}`}>{STATUS_LABEL[status]}</span>;
}
