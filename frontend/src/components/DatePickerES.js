/**
 * RutasFast - Selectores de fecha en español (dd/MM/yyyy)
 */
import React, { useState, useEffect } from 'react';
import { format, parse, isValid } from 'date-fns';
import { es } from 'date-fns/locale';
import { Calendar as CalendarIcon } from 'lucide-react';
import { Button } from './ui/button';
import { Calendar } from './ui/calendar';
import { Input } from './ui/input';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { cn } from '../lib/utils';

const parseISODate = (value) => {
  if (!value) return undefined;
  const d = parse(value, 'yyyy-MM-dd', new Date());
  return isValid(d) ? d : undefined;
};

export const DatePickerES = ({ value, onChange, placeholder = 'dd/mm/aaaa', className, testId }) => {
  const [open, setOpen] = useState(false);
  const date = parseISODate(value);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          className={cn('w-full justify-start text-left font-normal h-10', !date && 'text-stone-400', className)}
          data-testid={testId}
        >
          <CalendarIcon className="mr-2 h-4 w-4 shrink-0 text-stone-500" />
          {date ? format(date, 'dd/MM/yyyy') : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={date}
          defaultMonth={date}
          onSelect={(d) => {
            onChange(d ? format(d, 'yyyy-MM-dd') : '');
            setOpen(false);
          }}
          locale={es}
        />
      </PopoverContent>
    </Popover>
  );
};

export const DateTimePickerES = ({ value, onChange, className, testId }) => {
  const initial = value ? value.split('T') : ['', ''];
  const [datePart, setDatePart] = useState(initial[0]);
  const [timePart, setTimePart] = useState(initial[1] || '');

  useEffect(() => {
    // External reset (e.g. form cleared after submit)
    if (!value) {
      setDatePart('');
      setTimePart('');
    }
  }, [value]);

  const emit = (d, t) => {
    setDatePart(d);
    setTimePart(t);
    onChange(d && t ? `${d}T${t}` : '');
  };

  return (
    <div className="flex gap-2">
      <DatePickerES
        value={datePart}
        onChange={(d) => emit(d, timePart)}
        className={cn('flex-1', className)}
        testId={testId ? `${testId}-date` : undefined}
      />
      <Input
        type="time"
        value={timePart}
        onChange={(e) => emit(datePart, e.target.value)}
        className={cn('w-32', className)}
        data-testid={testId ? `${testId}-time` : undefined}
      />
    </div>
  );
};
