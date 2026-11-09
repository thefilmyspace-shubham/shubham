import Link from "next/link";
import { boardName } from "@/lib/ids";
import type { Student } from "@/lib/types";

/** Name, class, board, ID of the child; a switcher when the login has two or more children. */
export function ChildStrip({ list, current, basePath }: { list: Student[]; current: Student; basePath: string }) {
  return (
    <div className="bg-navy px-4 pt-1 pb-3 text-white">
      <div className="mx-auto max-w-lg">
        <p className="text-[17px] font-extrabold">{current.name}</p>
        <p className="text-[12.5px] text-white/75">
          Class {current.current_class} · {boardName(current.board)} · {current.code}
        </p>
        {list.length > 1 && (
          <div className="mt-2 flex gap-2 overflow-x-auto">
            {list.map((c) => (
              <Link
                key={c.id}
                href={`/parent/switch?child=${c.id}&next=${encodeURIComponent(basePath)}`}
                className={`rounded-full px-3 py-1 text-xs font-bold whitespace-nowrap ${c.id === current.id ? "bg-white text-navy" : "bg-white/15 text-white"}`}
              >
                {c.name.split(" ")[0]} · {c.current_class}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
