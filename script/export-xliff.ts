import { Command, Option } from "clipanion";
import { promises as fs } from "fs";
import * as path from "path";

export class XLIFFExporter extends Command {
  static paths = [["export"]];
  public file = Option.String({ required: true, name: "file" });

  async execute() {
    try {
      this.context.stdout.write(`Exporting to ${this.file}\n`);
      const filePath = path.resolve(process.cwd(), this.file);
      const raw = await fs.readFile(filePath, "utf8");

      this.context.stdout.write(raw);
    } catch (e) {
      if (e instanceof Error) {
        this.context.stdout.write(`Error: ${e.message}\n`);
      } else {
        this.context.stdout.write(`Unknown error\n`);
      }
    }
  }
}
