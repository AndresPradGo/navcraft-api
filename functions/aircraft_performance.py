"""
Useful Functions to Extract Aircraft Performance Data

Usage: 
- Import the required function and call it.
"""

from typing import Union, Any, List

from sqlalchemy import and_
from sqlalchemy.orm import Session

import models


def linear_interpolation(
    x1: Union[int, float],
    y1: Union[int, float],
    x2: Union[int, float],
    y2: Union[int, float],
    x_target: Union[int, float]
) -> Union[int, float]:
    """
    This function performs a 1-dimensional linear interpolation
    """

    # Calculate the slope
    slope = (y2 - y1) / (x2 - x1)

    # Use the slope to find the interpolated y-value at x_target
    y_value = y1 + slope * (x_target - x1)

    return y_value


def find_nearest_arrays(data: List[Any], target: Union[int, float], attr_name: str):
    """
    This function extracts 2 arrays from the data array. One array where 
    all the values of the attribute 'attr_name', are immediately less than 'target', and one 
    where they are greater than or equal to 'target'. If 'target' is smaller or higher than 
    all elements in data, the fucntion will return only one array, and it will truncate the 
    'target' to the smallest or highest value.
    """
    # Perform binary search
    low = 0
    high = len(data) - 1
    while low <= high:
        mid = (low + high) // 2
        if getattr(data[mid], attr_name) < target:
            low = mid + 1
        else:
            high = mid - 1

    # The "low" index points to the first number greater than or equal to x
    # The "high" index points to the last number less than x

    # Check for boundary conditions
    if high == -1:  # target is smaller than all elements in the list
        return (getattr(data[0], attr_name), [
            [row for row in data if getattr(
                row, attr_name) == getattr(data[low], attr_name)]
        ])
    if low == len(data):  # target is greater than or equal to all elements in the list
        return (getattr(data[-1], attr_name), [
            [row for row in data if getattr(
                row, attr_name) == getattr(data[high], attr_name)]
        ])

    return (target, [
        [row for row in data if getattr(
            row, attr_name) == getattr(data[high], attr_name)],
        [row for row in data if getattr(
            row, attr_name) == getattr(data[low], attr_name)]
    ])


def recursive_data_interpolation(
    input_names: List[str],
    index: int,
    output_names: List[str],
    interp_data_sets: List[List[Any]],
    targets: List[Union[int, float]]
):
    """
    This is a recursive function that interpolates values in a multidimensional table.
    """
    current_input = input_names[index]
    results = []
    for interp_data_set in interp_data_sets:
        targets[index], next_interp_data_sets = find_nearest_arrays(
            data=interp_data_set,
            target=targets[index],
            attr_name=current_input
        )
        if not current_input == input_names[-1]:
            deeper_layer_results_list, _ = recursive_data_interpolation(
                input_names=input_names,
                index=index + 1,
                output_names=output_names,
                interp_data_sets=next_interp_data_sets,
                targets=targets
            )
            deeper_layer_results_dict = {
                key: [
                    deeper_layer_result[key] for deeper_layer_result in deeper_layer_results_list
                ] for key in output_names
            }

        else:
            deeper_layer_results_dict = {
                key: [
                    getattr(data_set[0], key) for data_set in next_interp_data_sets
                ] for key in output_names
            }

        result = {}
        if len(deeper_layer_results_dict[output_names[0]]) == 2:
            for output_name, deeper_layer_results in deeper_layer_results_dict.items():
                result[output_name] = linear_interpolation(
                    x1=getattr(next_interp_data_sets[0][0], current_input),
                    y1=deeper_layer_results[0],
                    x2=getattr(next_interp_data_sets[1][0], current_input),
                    y2=deeper_layer_results[1],
                    x_target=targets[index]
                )
        else:
            for output_name, deeper_layer_results in deeper_layer_results_dict.items():
                result[output_name] = deeper_layer_results[0]

        results.append(result)

    return results, targets


def get_landing_takeoff_data(
    profile_id: int,
    is_takeoff: bool,
    weight_lb: int,
    pressure_alt_ft: int,
    temperature_c: int,
    runway_surface_id: int,
    head_wind: float,
    db_session: Session
):
    """
    This function performs a table lookup operation, and returns 
    the takeoff or landing data (groundroll_ft and obstacle_clearance_ft).
    """
    # define list of inputs and outputs to loop trhough
    inputs = ["weight_lb", "pressure_alt_ft", "temperature_c"]
    input_targets = [weight_lb, pressure_alt_ft, temperature_c]
    outputs = ["groundroll_ft", "obstacle_clearance_ft"]

    # Get table data
    is_tailwind = head_wind < 0
    performance_profile = db_session.query(models.PerformanceProfile).filter(
        models.PerformanceProfile.id == profile_id
    ).first()
    if is_takeoff:
        table_data = db_session.query(models.TakeoffPerformance).filter(
            models.TakeoffPerformance.performance_profile_id == profile_id
        ).order_by(
            models.TakeoffPerformance.weight_lb,
            models.TakeoffPerformance.pressure_alt_ft,
            models.TakeoffPerformance.temperature_c
        ).all()

        wind_correction = float(performance_profile.percent_increase_takeoff_tailwind_knot)\
            if is_tailwind else float(performance_profile.percent_decrease_takeoff_headwind_knot)

        surface_correction_data = db_session.query(models.SurfacePerformanceDecrease).filter(and_(
            models.SurfacePerformanceDecrease.performance_profile_id == profile_id,
            models.SurfacePerformanceDecrease.surface_id == runway_surface_id,
            models.SurfacePerformanceDecrease.is_takeoff.is_(True)
        )).first()

    else:
        table_data = db_session.query(models.LandingPerformance).filter(
            models.LandingPerformance.performance_profile_id == profile_id
        ).order_by(
            models.LandingPerformance.weight_lb,
            models.LandingPerformance.pressure_alt_ft,
            models.LandingPerformance.temperature_c
        ).all()

        wind_correction = float(performance_profile.percent_increase_landing_tailwind_knot)\
            if is_tailwind else float(performance_profile.percent_decrease_landing_headwind_knot)

        surface_correction_data = db_session.query(models.SurfacePerformanceDecrease).filter(and_(
            models.SurfacePerformanceDecrease.performance_profile_id == profile_id,
            models.SurfacePerformanceDecrease.surface_id == runway_surface_id,
            models.SurfacePerformanceDecrease.is_takeoff.is_(False)
        )).first()

    surface_correction = float(
        surface_correction_data.percent) if surface_correction_data is not None else 0

    # Get table data results
    result, adjusted_targets = recursive_data_interpolation(
        input_names=inputs,
        index=0,
        output_names=outputs,
        interp_data_sets=[table_data],
        targets=input_targets
    )
    result = result[0]

    # Apply wind corrections
    result["groundroll_ft"] = result["groundroll_ft"] - \
        head_wind * wind_correction * result["groundroll_ft"] / 100
    result["obstacle_clearance_ft"] = result["obstacle_clearance_ft"] - \
        head_wind * wind_correction * \
        result["obstacle_clearance_ft"] / 100

    # Apply runway surface corrections
    result["obstacle_clearance_ft"] = result["obstacle_clearance_ft"] + \
        surface_correction * result["groundroll_ft"] / 100
    result["groundroll_ft"] = result["groundroll_ft"] + \
        surface_correction * result["groundroll_ft"] / 100

    # Pre-process results and return
    result["groundroll_ft"] = int(round(result["groundroll_ft"], 0))
    result["obstacle_clearance_ft"] = int(
        round(result["obstacle_clearance_ft"], 0))

    new_input_targets = {
        value: adjusted_targets[i] for i, value in enumerate(inputs)}

    return result, new_input_targets


def get_climb_data(
    profile_id: int,
    weight_lb: int,
    pressure_alt_from_ft: int,
    pressure_alt_to_ft: int,
    temperature_c: int,
    available_distance_nm: int,
    db_session: Session
):
    """
    This function performs a table lookup operation, and returns 
    the climb data (time, fuel and distance to climb).

    Returns:
    - Dict: Truncated weight and pressure altitude. If the values 
      provided are higher than the max values in the table, it returns 
      the max values in the table.
    - Dict: 'time_min', 'fuel_gal' and 'distance_nm' values from the table.
    - int: if the available distance to climb to the desired pressure altitude, 
      is not enough, this values will be the approximate pressure altitude, the 
      aircraft can climb to, in the available distance

    """

    # Check it's actually a 1000ft climb
    if pressure_alt_to_ft - pressure_alt_from_ft < 1000:
        return (
            {
                "weight_lb": weight_lb,
                "pressure_alt_ft": pressure_alt_to_ft
            },
            {
                "time_min": 0,
                "fuel_gal": 0,
                "distance_nm": 0
            },
            pressure_alt_to_ft
        )

    # define list of inputs and outputs to loop trhough
    inputs = ["weight_lb", "pressure_alt_ft"]
    input_targets_list = [[weight_lb, pressure_alt_from_ft],
                          [weight_lb, pressure_alt_to_ft]]
    outputs = ["temperature_c", "time_min",
               "fuel_gal", "distance_nm"]
    table_results = []
    new_input_targets = []

    for index, input_targets in enumerate(input_targets_list):
        # Get table data
        table_data = db_session.query(models.ClimbPerformance).filter(
            models.ClimbPerformance.performance_profile_id == profile_id
        ).order_by(
            models.ClimbPerformance.weight_lb,
            models.ClimbPerformance.pressure_alt_ft
        ).all()

        # Get table data results
        table_result, adjusted_targets = recursive_data_interpolation(
            input_names=inputs,
            index=0,
            output_names=outputs,
            interp_data_sets=[table_data],
            targets=input_targets
        )

        table_results.append(table_result[0])

        new_input_targets.append({
            value: adjusted_targets[i] for i, value in enumerate(inputs)})

    # Apply temperature correction
    performance_profile = db_session.query(models.PerformanceProfile).filter(
        models.PerformanceProfile.id == profile_id
    ).first()

    temperature_correction_percent = float(
        performance_profile.percent_increase_climb_temperature_c) / 100
    standard_temperature = table_results[1]["temperature_c"]

    correction_value = temperature_correction_percent * \
        max(temperature_c - standard_temperature, 0) + 1

    for index, table_result in enumerate(table_results):
        for key, value in table_result.items():
            table_results[index][key] = float(value) * correction_value

    # Find difference
    result = {}
    result["time_min"] = table_results[1]["time_min"] - \
        table_results[0]["time_min"]
    result["fuel_gal"] = table_results[1]["fuel_gal"] - \
        table_results[0]["fuel_gal"]
    result["distance_nm"] = table_results[1]["distance_nm"] - \
        table_results[0]["distance_nm"]

    # Pre-process results
    result["time_min"] = int(round(result["time_min"], 0))
    result["fuel_gal"] = float(round(result["fuel_gal"], 2))
    result["distance_nm"] = int(round(result["distance_nm"], 0))

    # Check distance
    enough_distance = available_distance_nm >= result["distance_nm"]
    if enough_distance:
        actual_pressure_altitude = pressure_alt_to_ft
    else:
        # If not enough distance, need to approximate actual altitude
        avrg_speed = result["distance_nm"] / result["time_min"]
        avrg_fpm = (new_input_targets[1]["pressure_alt_ft"] -
                    new_input_targets[0]["pressure_alt_ft"]) / result["time_min"]
        avrg_distance = available_distance_nm / correction_value
        actual_pressure_altitude = int(
            round(pressure_alt_from_ft + avrg_fpm * avrg_distance / avrg_speed, 0))

    # Return result
    return new_input_targets[1], result, actual_pressure_altitude


def get_cruise_data(
    profile_id: int,
    weight_lb: int,
    pressure_alt_ft: int,
    temperature_c: int,
    bhp_percent: int,
    db_session: Session
):
    """
    This function performs a table lookup operation, and returns 
    the cruise data (ktas, gph, rpm).
    """

    # define list of inputs and outputs to loop trhough
    inputs = ["weight_lb", "pressure_alt_ft", "temperature_c", "bhp_percent"]
    input_targets = [weight_lb, pressure_alt_ft, temperature_c, bhp_percent]
    outputs = ["ktas", "gph", "rpm"]

    # Get table data
    table_data = db_session.query(models.CruisePerformance).filter(
        models.CruisePerformance.performance_profile_id == profile_id
    ).order_by(
        models.CruisePerformance.weight_lb,
        models.CruisePerformance.pressure_alt_ft,
        models.CruisePerformance.temperature_c,
        models.CruisePerformance.bhp_percent
    ).all()

    # Get table data results
    result, adjusted_targets = recursive_data_interpolation(
        input_names=inputs,
        index=0,
        output_names=outputs,
        interp_data_sets=[table_data],
        targets=input_targets
    )
    result = result[0]

    # Pre-process table data results
    result["ktas"] = int(round(result["ktas"], 0))
    result["gph"] = float(round(result["gph"], 2))
    result["rpm"] = int(round(result["rpm"], 0))

    new_input_targets = {
        value: adjusted_targets[i] for i, value in enumerate(inputs)}

    return result, new_input_targets
